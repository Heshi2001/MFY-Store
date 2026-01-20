from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Cart, Order, OrderItem, ProductVariant, ProductImage, Wishlist, Review, UserProfile, Address, Coupon, CartItem, Category, Banner, HomeSection, PromoBanner,FAQ, StockNotification, CouponUsage, AboutPage, SocialLink, Value, TeamMember, Service, Client,SavedItem, ReturnRequest, NewsletterSubscriber, Payment
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.html import escape, format_html
from django.contrib.auth import login
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from .forms import ContactForm, ReviewForm, UserUpdateForm
from django.contrib.auth.models import User
from .models import EmailOTP
import json
import random
import razorpay
from django.http import JsonResponse
from django.http import HttpResponse
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import get_user_model
from allauth.account.views import LoginView
from allauth.account.forms import SignupForm
from allauth.account.views import SignupView
from .forms import AddressForm
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth import update_session_auth_hash
from django.urls import reverse_lazy
import logging
from django.conf import settings
from django.contrib.auth import login as auth_login
from django.views.decorators.http import require_POST
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import ProductSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Sum
from django.db.models import Q
from django.template.loader import render_to_string
from .utils import get_or_create_session_key 
from django.db.models import Avg, Count
from django.core.paginator import Paginator
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Case, When, Min, F

logger = logging.getLogger(__name__)

User = get_user_model()

def attach_product_display_data(product):
    """
    Attach pricing, stock, discount & image info to product
    (frontend-safe helper)
    """
    # 🖼 Image
    if product.image_mode == "custom" and product.custom_image:
        product.first_image = product.custom_image
    else:
        product.first_image = product.images.first()

    # 💰 Base variant
    base_variant = product.get_base_variant()

    if base_variant:
        product.display_price = base_variant.offer_price or base_variant.price
        product.original_price = base_variant.price
        product.offer_price = base_variant.offer_price
        product.discount_percent = base_variant.discount_percent
    else:
        product.display_price = None
        product.original_price = None
        product.offer_price = None
        product.discount_percent = None

    return product

def index(request):
    query = request.GET.get('q')

    if query:
        products = (
            Product.objects
            .filter(name__icontains=query)
            .prefetch_related("images", "variants")
        )
    else:
        products = (
            Product.objects
            .prefetch_related("images", "variants")
            .order_by('-id')[:6]
        )

    # 🟢 Attach pricing + image info
    for product in products:
        attach_product_display_data(product)

    # ✅ Categories
    top_categories = Category.objects.filter(parent__isnull=True)
    categories_with_children = (
        Category.objects
        .filter(parent__isnull=True)
        .prefetch_related('children')
    )

    # ✅ Banners
    banners = Banner.objects.filter(active=True).order_by('order')

    # ✅ Promo Banner
    promo_banner = (
        PromoBanner.objects.filter(is_active=True)
        .filter(Q(start_date__lte=timezone.now()) | Q(start_date__isnull=True))
        .filter(Q(end_date__gte=timezone.now()) | Q(end_date__isnull=True))
        .order_by('-created_at')
        .first()
    )
    promo_banner_text = promo_banner.message if promo_banner else ""

    # ✅ Dynamic Homepage Sections
    home_sections = HomeSection.objects.filter(active=True).order_by('order')
    dynamic_sections = []

    for section in home_sections:
        if section.category:
            section_products = (
                Product.objects.filter(
                    category__in=section.category.get_descendants(include_self=True)
                )
                .prefetch_related("images", "variants")
                .order_by('-id')[:section.product_limit]
            )
        else:
            section_products = (
                Product.objects
                .prefetch_related("images", "variants")
                .order_by('-id')[:section.product_limit]
            )

        for product in section_products:
            attach_product_display_data(product)

        dynamic_sections.append({
            "title": section.title,
            "products": section_products,
        })

    return render(request, 'store/index.html', {
        'products': products,
        'categories': top_categories,
        'sidebar_categories': categories_with_children,
        'banners': banners,
        'dynamic_sections': dynamic_sections,
        'promo_banner_text': promo_banner_text,
    })

def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)

    descendants = category.get_descendants(include_self=True)

    products = (
        Product.objects
        .filter(category__in=descendants)
        .prefetch_related("images", "variants")
        .distinct()
    )

    sort_option = request.GET.get("sort")

    if sort_option == "low-high":
        products = products.annotate(
            sort_price=Min(
                Case(
                    When(variants__offer_price__isnull=False, then=F("variants__offer_price")),
                    default=F("variants__price"),
                )
            )
        ).order_by("sort_price")

    elif sort_option == "high-low":
        products = products.annotate(
            sort_price=Min(
                Case(
                    When(variants__offer_price__isnull=False, then=F("variants__offer_price")),
                    default=F("variants__price"),
                )
            )
        ).order_by("-sort_price")

    elif sort_option == "rating":
        products = products.annotate(
            avg_rating=Avg("reviews__rating")
        ).order_by("-avg_rating")

    elif sort_option == "newest":
        products = products.order_by("-id")

    for product in products:
        attach_product_display_data(product)

    # ❤️ Wishlist
    if request.user.is_authenticated:
        wishlist_ids = list(
            Wishlist.objects
            .filter(user=request.user)
            .values_list("product_id", flat=True)
        )
    else:
        wishlist_ids = []

    # 🛒 Cart count
    if request.user.is_authenticated:
        cart_data = Cart.objects.for_user_or_session(user=request.user)
    else:
        session_key = get_or_create_session_key(request)
        cart_data = Cart.objects.for_user_or_session(session_key=session_key)

    cart_items_count = (
        cart_data["cart"].items.aggregate(total=Sum("quantity"))["total"] or 0
    )

    context = {
        "category": category,
        "products": products,
        "cart_items_count": cart_items_count,
        "wishlist_ids": wishlist_ids,
    }

    if request.headers.get("HX-Request"):
        return render(request, "store/partials/_product_grid.html", context)

    return render(request, "store/category_products.html", context)

@login_required
def account_dashboard(request):
    # Ensure user has a profile
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Fetch related data
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    wishlist = Wishlist.objects.filter(user=request.user)
    user_coupons = Coupon.objects.filter(
        is_active=True
    ).filter(
        models.Q(coupon_type="GENERIC") |
        models.Q(coupon_type="FIRST_ORDER") |
        models.Q(coupon_type="MIN_SPEND") |
        models.Q(coupon_type="BUY_X_GET_Y") |
        models.Q(coupon_type="USER_SPECIFIC", specific_user=request.user)
    )

    # --------------------------------------
    # 🔥 Prepare "recent orders" JSON for JS
    # --------------------------------------
    orders_json = []

    for order in orders[:5]:  # Only latest 5 orders
        items = order.items.select_related("product")

        # Pick first product image
        first_image_url = None
        if items:
            product = items[0].product

            # Match your product image logic
            if getattr(product, "image_mode", None) == "custom" and product.custom_image:
                first_image_url = product.custom_image.url
            else:
                first_gallery = product.images.first()
                if first_gallery and first_gallery.image:
                    first_image_url = first_gallery.image.url

        orders_json.append({
            "id": order.id,
            "total": float(order.total_price),
            "status": order.status,
            "date": order.created_at.strftime("%b %d, %Y"),
            "image": first_image_url or "/static/global/default-product.png"
        })

    # --------------------------------------
    # Final context
    # --------------------------------------
    context = {
        "profile": profile,
        "addresses": addresses,
        "orders": orders,
        "wishlist": wishlist,
        "orders_count": orders.count(),      # 👈
        "wishlist_count": wishlist.count(),
        "user_coupons": user_coupons,
        "orders_json": json.dumps(orders_json, cls=DjangoJSONEncoder),  # for JS
    }

    return render(request, "account/dashboard.html", context)

@login_required
def update_avatar(request):
    if request.method == "POST":
        profile = request.user.userprofile

        if 'avatar' in request.FILES:
            profile.profile_image = request.FILES['avatar']
            profile.save()
            messages.success(request, "Your profile picture has been updated!")
        else:
            messages.error(request, "No image was selected.")

    return redirect('account_dashboard')

@login_required
def account_settings(request):
    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("account_dashboard")  # go back to dashboard after saving
    else:
        form = UserUpdateForm(instance=request.user)

    return render(request, "account/settings.html", {"form": form})

@login_required
def addresses(request):
    user_addresses = Address.objects.filter(user=request.user)
    return render(request, "account/addresses.html", {"addresses": user_addresses})

@login_required
@require_POST
def set_default_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)

    # Remove old default
    Address.objects.filter(user=request.user, is_default=True).exclude(pk=pk).update(is_default=False)

    # Set new default
    address.is_default = True
    address.save()

    return redirect("account_addresses")

@login_required
def address_add(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user

            # FORCE required hidden/default values
            address.country = "India"        # default country
            address.address_type = "home"    # default to home

            # First address → make default
            if not Address.objects.filter(user=request.user).exists():
                address.is_default = True
            else:
                address.is_default = False

            address.save()

            # Sync first/last name to User model
            if address.first_name and address.last_name:
                request.user.first_name = address.first_name
                request.user.last_name = address.last_name
                request.user.save()

            return redirect("account_addresses")  # Works

        else:
            print(form.errors)  # Debug if needed

    else:
        form = AddressForm()

    return render(request, "account/address_form.html", {"form": form})

@login_required
def edit_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            address = form.save(commit=False)
            if address.is_default:
                Address.objects.filter(user=request.user, is_default=True).exclude(pk=address.pk).update(is_default=False)
            address.save()
            # ✅ Sync names into User model again
            if address.first_name and address.last_name:
                request.user.first_name = address.first_name
                request.user.last_name = address.last_name
                request.user.save()

            return redirect("account_addresses")
    else:
        form = AddressForm(instance=address)
    return render(request, "account/address_form.html", {"form": form})

@login_required
def address_delete_confirm(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    return render(request, "account/address_confirm_delete.html", {"address": address})

@login_required
@require_POST
def delete_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.delete()
    return JsonResponse({"success": True})

def products_view(request):
    products = (
        Product.objects
        .prefetch_related('images', 'variants')
        .order_by('-id')
    )

    for product in products:
        # 🖼 Image
        if product.image_mode == "custom" and product.custom_image:
            product.first_image = product.custom_image
        else:
            product.first_image = product.images.first()

        # 🟢 BASE VARIANT (CHEAPEST)
        base_variant = product.get_base_variant()

        if base_variant:
            product.display_price = base_variant.offer_price or base_variant.price
            product.original_price = base_variant.price
            product.offer_price = base_variant.offer_price
            product.discount_percent = base_variant.discount_percent
            
        else:
            product.display_price = None
            product.original_price = None
            product.offer_price = None
            product.discount_percent = None

        # ⭐ Ratings
        avg_rating = product.reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        product.avg_rating = round(avg_rating, 1)
        product.total_reviews = product.reviews.count()

    return render(request, 'store/products.html', {
        "products": products,
    })

@login_required
def orders_list(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")

    for order in orders:
        if not order.estimated_delivery:
            order.auto_estimated_delivery = order.created_at + timedelta(days=5)
        else:
            order.auto_estimated_delivery = order.estimated_delivery

    wishlist_items = Wishlist.objects.filter(user=request.user)

    return render(request, "store/orders.html", {
        "orders": orders,
        "wishlist_items": wishlist_items,  
    })

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.items.select_related("product").all()

    # 🧾 Base totals — same as checkout page
    subtotal = sum(item.total_price for item in items)

    shipping = (subtotal * Decimal("0.05")).quantize(Decimal("0.01"))
    tax = (subtotal * Decimal("0.10")).quantize(Decimal("0.01"))

    total_before_discount = subtotal + shipping + tax

    # If you stored discount_percent in order model
    if order.discount_percent:
        discount_amount = (total_before_discount * order.discount_percent / 100).quantize(Decimal("0.01"))
        total = total_before_discount - discount_amount
    else:
        discount_amount = Decimal("0.00")
        total = total_before_discount

    return render(request, "store/order_detail.html", {
        "order": order,
        "items": items,
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "total_before_discount": total_before_discount,
        "discount_amount": discount_amount,
        "total": total,
    })

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variants = product.variants.select_related("color", "size")
    main_images = product.images.filter(is_main=True)

    # 🖼 First image
    if product.image_mode == "custom" and product.custom_image:
        first_image_url = product.custom_image.url
    else:
        first_image_url = main_images.first().image.url if main_images.exists() else ""

    # ⭐ Reviews
    reviews = Review.objects.filter(product=product).order_by('-id')
    rating_stats = reviews.aggregate(
        avg_rating=Avg('rating'),
        total_reviews=Count('id')
    )
    average_rating = round(rating_stats['avg_rating'] or 0, 1)
    total_reviews = rating_stats['total_reviews']

    # 🎯 Sizes & Colors
    sizes = list({v.size for v in variants if v.size})
    colors = list({v.color for v in variants if v.color})

    # 🎨 Variant map (color → images + price)
    variant_map_list = []

    for variant in variants:
        if not variant.color:
            continue

        color_images = variant.color.images.all().order_by("-is_main")
        image_urls = [img.image.url for img in color_images]

        if not image_urls:
            if variant.image:
                image_urls = [variant.image.url]
            elif first_image_url:
                image_urls = [first_image_url]

        variant_map_list.append({
            "color": variant.color.id,
            "images": image_urls,
            "price": float(variant.price),
            "offer_price": float(variant.offer_price) if variant.offer_price else None,
        })

    variant_map = json.dumps(variant_map_list)

    # ❤️ Wishlist
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = list(
            Wishlist.objects.filter(user=request.user)
            .values_list('product_id', flat=True)
        )

    # 🔥 Recommended
    recommended_products = Product.objects.filter(
        category=product.category
    ).exclude(id=product.id)[:4]

    # 💰 Savings (BASE VARIANT)
    base_variant = product.get_base_variant()
    
    base_price_data = {
        "price": float(base_variant.price) if base_variant else None,
        "offer_price": float(base_variant.offer_price)
        if base_variant and base_variant.offer_price else None,
    }
    
    you_save = 0
    if base_variant and base_variant.offer_price:
        you_save = base_variant.price - base_variant.offer_price

    context = {
        'product': product,
        'variants': variants,
        'sizes': sizes,
        'colors': colors,
        'variant_map': variant_map,
        'images': main_images,
        'wishlist_product_ids': wishlist_product_ids,
        'recommended_products': recommended_products,
        'reviews': reviews,
        'form': ReviewForm(),
        'first_image_url': first_image_url,
        'average_rating': average_rating,
        'total_reviews': total_reviews,
        'you_save': you_save,
        'base_variant': base_variant,                     # ✅ template usage
        'base_price_data': json.dumps(base_price_data), 
    }

    return render(request, 'store/product_detail.html', context)

@method_decorator(cache_page(60*5), name="list")
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        Product.objects
        .prefetch_related("images", "variants__color", "variants__size")
        .select_related("category")
    )
    serializer_class = ProductSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ["dealer", "category__id", "category__name", "sku"]
    search_fields = ["name", "description", "sku"]
    ordering_fields = ["name"]
    ordering = ["name"]

@login_required
def add_to_wishlist(request, product_id):
    """
    Toggle wishlist status for a given product.
    If product is already in wishlist, remove it.
    Otherwise, add it.
    """
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)

    if not created:
        # Already in wishlist → remove it
        wishlist_item.delete()
        return JsonResponse({'added': False, 'message': 'Removed from wishlist'})
    else:
        # Added to wishlist
        return JsonResponse({'added': True, 'message': 'Added to wishlist'})


@login_required
def remove_from_wishlist(request, product_id):
    """
    Explicitly remove a product from wishlist (used in wishlist page).
    """
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    return redirect('wishlist')

@login_required
def wishlist_view(request):
    wishlist_items = (
        Wishlist.objects
        .filter(user=request.user)
        .select_related('product')
        .prefetch_related('product__images', 'product__variants')
    )

    for item in wishlist_items:
        attach_product_display_data(item.product)  # ✅ THIS IS THE KEY

    return render(
        request,
        'store/wishlist.html',
        {'wishlist_items': wishlist_items}
    )

@login_required
def toggle_price_alert(request, product_id):
    wishlist_item = get_object_or_404(Wishlist, user=request.user, product_id=product_id)
    wishlist_item.alert_enabled = not wishlist_item.alert_enabled
    wishlist_item.save()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'alert_enabled': wishlist_item.alert_enabled})
    return redirect('wishlist')

@login_required
def notify_me_stock(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    _, created = StockNotification.objects.get_or_create(
        user=request.user,
        product=product
    )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "message": "🔔 We’ll notify you when it’s back!" if created
            else "✅ You’re already subscribed!"
        })

    messages.success(
        request,
        "🔔 We’ll notify you when this product is back in stock."
        if created else
        "✅ You’re already subscribed for stock updates."
    )

    return redirect(request.META.get("HTTP_REFERER", "wishlist"))

@csrf_exempt  # Remove this in production if not needed
def submit_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user if request.user.is_authenticated else None
            review.save()
            return redirect('product_detail', product_id=product.id)

    return redirect('product_detail', product_id=product.id)

@login_required
def checkout(request):
    # Get user cart
    cart_data = Cart.objects.for_user_or_session(
        user=request.user, session_key=request.session.session_key
    )
    cart = cart_data["cart"]
    items = cart_data["items"]

    if not items:
        return redirect("view_cart")

    # ---------------------------------------------------
    # 1️⃣ Recalculate totals using SAME function as cart
    # ---------------------------------------------------
    subtotal, shipping, tax, total_before_discount = calculate_cart_totals(cart)

    # ---------------------------------------------------
    # 2️⃣ Get applied coupon from session (set in cart)
    # ---------------------------------------------------
    coupon_code = request.session.get("selected_coupon")
    discount_amount = Decimal("0.00")
    applied_coupon = None

    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)

            # Validate subtotal
            if coupon.is_valid(user=request.user, total=subtotal):
                applied_coupon = coupon
                discount_amount = (subtotal * coupon.discount_percent / 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            else:
                request.session.pop("selected_coupon", None)

        except Coupon.DoesNotExist:
            request.session.pop("selected_coupon", None)

    # ---------------------------------------------------
    # 3️⃣ Final total after discount
    # ---------------------------------------------------
    total = (subtotal - discount_amount) + shipping + tax

    # ---------------------------------------------------
    # 4️⃣ Create Razorpay Order
    # ---------------------------------------------------
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    razorpay_order = client.order.create({
        "amount": int(total * 100),  # convert to paise
        "currency": "INR",
        "payment_capture": "1",
    })

    request.session["razorpay_order_id"] = razorpay_order["id"]

    # ---------------------------------------------------
    # 5️⃣ Render checkout page
    # ---------------------------------------------------
    return render(request, "store/checkout.html", {
        "cart": cart,
        "items": items,
        "addresses": Address.objects.filter(user=request.user),

        # Totals
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "discount_amount": discount_amount,
        "total_before_discount": total_before_discount,
        "total": total,

        # Coupon info
        "applied_coupon": applied_coupon,

        # Razorpay
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "razorpay_order": razorpay_order,
    })

@csrf_exempt
@login_required
def payment_success(request):
    """
    Razorpay callback – verifies signature, creates dealer/self orders,
    reduces stock, clears cart, and triggers external dealer APIs.
    Redirects to dynamic Order Success page.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            # 🟢 Verify Razorpay signature
            params_dict = {
                "razorpay_order_id": data.get("razorpay_order_id"),
                "razorpay_payment_id": data.get("razorpay_payment_id"),
                "razorpay_signature": data.get("razorpay_signature"),
            }
            client.utility.verify_payment_signature(params_dict)

            # 🟢 Get cart
            cart_data = Cart.objects.for_user_or_session(
                user=request.user, session_key=request.session.session_key
            )
            cart = cart_data["cart"]
            items = cart_data["items"]

            if not items:
                return redirect("view_cart")

            address_id = request.session.get("checkout_address_id")
            shipping_address = Address.objects.filter(id=address_id, user=request.user).first()

            # 🟢 Create dealer-wise orders
            dealer_orders = {}
            for item in items:
                dealer = getattr(item.product, "dealer", "Self")  # default Self

                if dealer not in dealer_orders:
                    # ALWAYS create new order on new checkout
                    order = Order.objects.create(
                        user=request.user,
                        total_price=0,
                        payment_id=data["razorpay_order_id"],
                        shipping_address=shipping_address,
                        billing_address=shipping_address,

                        status="Processing",
                        payment_status="PAID",

                        # 🟢 Snapshot
                        shipping_first_name = shipping_address.first_name,
                        shipping_last_name = shipping_address.last_name,
                        shipping_phone = shipping_address.phone,
                        shipping_address_line1 = shipping_address.address_line1,
                        shipping_address_line2 = shipping_address.address_line2,
                        shipping_city = shipping_address.city,
                        shipping_state = shipping_address.state,
                        shipping_country = shipping_address.country,
                        shipping_postal_code = shipping_address.postal_code,
                    )
                    dealer_orders[dealer] = order

                # Do NOT reuse old order - always use the one just assigned
                order = dealer_orders[dealer]

                # Out of stock check
                if item.product.stock < item.quantity and dealer == "Self":
                    return render(request, "store/out_of_stock.html", {"product": item.product})
                
                # ✅ Determine correct price (NEW MODEL LOGIC)
                if item.variant:
                    price = item.variant.offer_price or item.variant.price
                else:
                    price = item.product.price

                # Create OrderItem
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    variant=item.variant,
                    quantity=item.quantity,
                    price=price,
                )

                order.total_price += price * item.quantity
                order.save()

                # Reduce stock for self-dealer items
                if dealer == "Self":
                    item.product.stock -= item.quantity
                    item.product.save()

                # 🟢 Trigger External Dealer API (if needed)
                if dealer == "Qikink":
                    from store.qikink_api import create_test_order
                    response = create_test_order(order)
                    print("Qikink response:", response)
                elif dealer == "Printrove":
                    print(f"Send order {order.id} to Printrove API")

            # 🟢 Apply coupon to orders
            coupon_code = request.session.get("applied_coupon_code")
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code=coupon_code)
                    CouponUsage.objects.get_or_create(user=request.user, coupon=coupon)

                    for order in dealer_orders.values():
                        order.coupon = coupon
                        order.discount_percent = coupon.discount_percent
                        order.save()

                    del request.session["applied_coupon_code"]
                    request.session.modified = True
                except Coupon.DoesNotExist:
                    pass

            # 🟢 Final Calculation: subtotal + shipping + tax - discount (Save to DB)
            from decimal import Decimal, ROUND_HALF_UP

            for order in dealer_orders.values():
                order_items = order.items.all()
                subtotal = sum(item.total_price for item in order_items)

                shipping = (subtotal * Decimal("0.05")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                tax = (subtotal * Decimal("0.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                total_before_discount = subtotal + shipping + tax

                if order.discount_percent:
                    discount_amount = (total_before_discount * order.discount_percent / 100).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                else:
                    discount_amount = Decimal("0.00")

                total = total_before_discount - discount_amount

                # 🟢 Save final totals
                order.total_price = total
                order.discount_amount = discount_amount
                order.save()

            # 🟢 Clear cart
            cart.items.all().delete()

            # 🟢 Pick one of the created dealer orders to show success
            main_order = max(dealer_orders.values(), key=lambda x: x.id)
            
            # 🟢 CREATE PAYMENT OBJECT (Important)
            Payment.objects.create(
                user=request.user,
                order=main_order,
                method="RAZORPAY",
                status="PAID",
                amount=main_order.total_price,
                transaction_id=data.get("razorpay_payment_id"),
                gateway_response=data
            )               

            # Estimated delivery date (example: +5 days)
            from datetime import timedelta, date
            estimated_delivery = (date.today() + timedelta(days=5)).strftime("%b %d, %Y")

            # 🟢 Get items for display
            order_items = OrderItem.objects.filter(order=main_order)

            # 🟢 Render Dynamic Order Success Page
            return render(request, "store/order_success.html", {
                "order": main_order,
                "items": order_items,
                "estimated_delivery": estimated_delivery,
            })

        except razorpay.errors.SignatureVerificationError:
            messages.error(request, "Payment verification failed.")
            return redirect("view_cart")
        except Exception as e:
            messages.error(request, f"Payment error: {e}")
            return redirect("view_cart")

    return JsonResponse({"success": False, "error": "Invalid request"})

@login_required
def order_success(request, order_id=None):
    if order_id:
        order = get_object_or_404(Order, id=order_id, user=request.user)
    else:
        order = Order.objects.filter(user=request.user).order_by('-created_at').first()
        if not order:
            return redirect('orders')

    items = order.items.select_related('product').all()
    estimated_delivery = order.created_at + timedelta(days=5)
    formatted_delivery = estimated_delivery.strftime("%b %d, %Y")

    return render(request, "store/order_success.html", {
        "order": order,
        "items": items,
        "estimated_delivery": formatted_delivery,
    })

def about(request):
    """Render About page with all content sections"""
    about_page = AboutPage.objects.first()  # Only one AboutPage expected
    social_links = SocialLink.objects.all()
    values = Value.objects.all()
    team_members = TeamMember.objects.prefetch_related("social_links").all()
    services = Service.objects.all()
    clients = Client.objects.all()

    context = {
        "about_page": about_page,
        "social_links": social_links,
        "values": values,
        "team_members": team_members,
        "services": services,
        "clients": clients,
        "about_text": "We are a brand committed to offering innovative and sustainable products for our customers.",
    }

    return render(request, "store/about.html", context)

def contact_view(request):
    # contact info cards (moved from template)
    infos = [
        {'icon': 'fa-headset', 'title': 'Customer Support', 'desc': 'We reply within 24 hours'},
        {'icon': 'fa-envelope', 'title': 'example@gmail.com', 'desc': 'Drop us an email'},
        {'icon': 'fa-location-dot', 'title': 'Our Lady of Presentation Church', 'desc': 'India 🏡'},
    ]

    form = ContactForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        contact = form.save()
        # send email notification
        send_mail(
            subject=contact.subject,
            message=f"Message from {contact.name} <{contact.email}>:\n\n{contact.message}",
            from_email=contact.email,
            recipient_list=['euliheshicleetus2001@gmail.com'],  # change to your email
            fail_silently=False,
        )

        return redirect('contact_thanks')

    return render(request, 'store/contact.html', {'form': form, 'infos': infos})

def contact_thanks(request):
    return render(request, 'store/contact_thanks.html')

# ---------------------------
# Main Search Page
# ---------------------------
def search_view(request):
    query = request.GET.get('query', '').strip()
    sort = request.GET.get('sort', '')
    products = []

    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()

        # Sorting
        if sort == 'price_asc':
            products = products.order_by('price')
        elif sort == 'price_desc':
            products = products.order_by('-price')
        elif sort == 'newest':
            products = products.order_by('-id')

    return render(request, 'store/search_results.html', {
        'products': products,
        'query': query,
        'sort': sort,
    })

# ---------------------------
# AJAX JSON Search Suggestions
# ---------------------------
def search_suggestions(request):
    query = request.GET.get("q", "").strip()
    results = []

    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()[:6]

        for p in products:
            highlighted_name = escape(p.name)
            q_lower = query.lower()
            name_lower = p.name.lower()
            start = name_lower.find(q_lower)
            if start != -1:
                end = start + len(query)
                highlighted_name = format_html(
                    '{}<span class="bg-yellow-200">{}</span>{}',
                    p.name[:start],
                    p.name[start:end],
                    p.name[end:]
                )

            results.append({
                "name": p.name,
                "highlight": highlighted_name,
                "url": p.get_absolute_url(),
                "category": p.category.name if p.category else "",
                "image": p.get_main_image_url(),
            })

    return JsonResponse(results, safe=False)

class CombinedLoginView(LoginView):
    template_name = "account/login.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["signup_form"] = SignupForm()
        ctx["active_tab"] = self.request.session.pop("active_tab", "login")
        return ctx

    def form_invalid(self, form):
        # 🔥 ALWAYS force login tab on auth failure
        self.request.session["active_tab"] = "login"
        return super().form_invalid(form)

def send_email_otp(request):
    """
    Accepts POST(email) -> creates OTP row, emails user, stores user id in session,
    then redirects to verify page. Always handles exceptions and logs them.
    """
    if request.method != "POST":
        return redirect("account_login")

    email = (request.POST.get("email") or "").strip()

    if not email:
        messages.error(request, "Please enter an email address.")
        request.session["active_tab"] = "otp"
        return redirect("account_login")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        messages.error(request, "No account found with this email.")
        request.session["active_tab"] = "otp"
        return redirect("account_login")

    otp = f"{random.randint(100000, 999999)}"

    try:
        EmailOTP.objects.filter(user=user).delete()
        EmailOTP.objects.create(user=user, otp=otp)
    except Exception:
        logger.exception("Failed to save OTP to DB for %s", email)
        messages.error(request, "Server error. Please try again shortly.")
        request.session["active_tab"] = "otp"
        return redirect("account_login")

    try:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.EMAIL_HOST_USER
        send_mail(
            subject="Your OTP Code",
            message=f"Your OTP code is {otp}",
            from_email=from_email,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send OTP email to %s", email)
        messages.error(request, "Unable to send OTP email. Please try again later.")
        request.session["active_tab"] = "otp"
        return redirect("account_login")

    # Save user id for verification
    request.session["otp_user_id"] = user.id

    messages.success(request, "OTP sent to your email.")
    return redirect("verify_email_otp")

def verify_email_otp(request):
    if request.method == "POST":
        try:
            otp_entered = (request.POST.get("otp") or "").strip()
            user_id = request.session.get("otp_user_id")

            if not user_id:
                messages.error(request, "Session expired. Please request a new OTP.")
                return redirect("account_login")

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                messages.error(request, "User not found. Please request OTP again.")
                return redirect("account_login")

            try:
                otp_obj = EmailOTP.objects.get(user=user, otp=otp_entered)
            except EmailOTP.DoesNotExist:
                messages.error(request, "Invalid OTP. Please try again.")
                return render(request, "store/verify_email_otp.html")

            # expiry check
            try:
                if otp_obj.is_expired():
                    otp_obj.delete()
                    messages.error(request, "OTP expired. Please request again.")
                    return redirect("account_login")
            except Exception:
                logger.exception("Error checking OTP expiry for user %s", user.email)
                messages.error(request, "Server error while verifying OTP. Try again.")
                return redirect("account_login")

            # Valid OTP -> login and cleanup
            otp_obj.delete()

            # Ensure user is active
            if not user.is_active:
                messages.error(request, "Your account is inactive. Contact support.")
                return redirect("account_login")

            # Log the attempt
            logger.info("Attempting to log in user %s (id=%s) via OTP", user.email, user.id)

            # Use auth_login explicitly
            auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            # Force-save session (optional) and remove otp_user_id
            request.session.modified = True
            request.session.pop("otp_user_id", None)

            messages.success(request, "OTP verified — you are now logged in.")
            return redirect("otp_success")

        except Exception:
            logger.exception("Unexpected error in verify_email_otp")
            messages.error(request, "Unexpected server error. Please try again.")
            return redirect("account_login")


    # GET
    return render(request, "store/verify_email_otp.html")

def otp_success(request):
    next_url = request.GET.get("next") or "/account/dashboard/"
    return redirect(next_url)

def payments(request):
    # Get latest order of the user
    order = Order.objects.filter(user=request.user).order_by("-created_at").first()

    # Get payment for that order (OneToOne → .payment)
    payment = order.payment if order and hasattr(order, "payment") else None

    return render(request, "store/payments.html", {
        "payment": payment,
        "order": order,
    })

class CustomPasswordChangeView(PasswordChangeView):
    template_name = "account/password_change.html"
    success_url = reverse_lazy("account_dashboard")

    def form_valid(self, form):
        # Save the new password
        response = super().form_valid(form)

        # Keep the user logged in after password change
        update_session_auth_hash(self.request, form.user)

        # Add a success message
        messages.success(self.request, "✅ Your password has been updated successfully!")

        return response

def account_offers(request):
    coupons = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_to__gte=timezone.now(),
    ).filter(
        models.Q(coupon_type="GENERIC") |
        models.Q(coupon_type="FIRST_ORDER") |
        models.Q(coupon_type="MIN_SPEND") |
        models.Q(coupon_type="BUY_X_GET_Y") |
        models.Q(coupon_type="USER_SPECIFIC", specific_user=request.user)
    )

    # Add dynamic timer (hours, mins, secs)
    for c in coupons:
        c.hh, c.mm, c.ss = c.time_left()
    
    return render(request, "store/offers.html", {
        "coupons": coupons,
    })

@require_POST
def apply_coupon_ajax(request):
    data = json.loads(request.body)
    code = data.get("coupon_code", "").strip()

    # Get session/user cart
    session_key = get_or_create_session_key(request)

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        cart = Cart.objects.filter(session_key=session_key).first()

    if not cart:
        return JsonResponse({"success": False, "message": "Cart empty"})

    # Base totals using your calculate_cart_totals()
    subtotal, shipping_total, tax_total, grand_total = calculate_cart_totals(cart)

    # Validate coupon
    try:
        coupon = Coupon.objects.get(code__iexact=code, is_active=True)

        if not coupon.is_valid(request.user, subtotal):
            return JsonResponse({"success": False, "message": "Coupon not valid"})
    except Coupon.DoesNotExist:
        return JsonResponse({"success": False, "message": "Invalid coupon code"})

    # Calculate discount
    discount_percent = Decimal(str(coupon.discount_percent))
    discount_amount = (subtotal * discount_percent) / Decimal("100")

    final_total = (subtotal - discount_amount) + shipping_total + tax_total

    # Save in session
    request.session["selected_coupon"] = coupon.code
    request.session["coupon_just_applied"] = True

    # Return ALL totals so JS never breaks
    return JsonResponse({
        "success": True,
        "coupon": coupon.code,
        "subtotal": str(subtotal),
        "shipping_total": str(shipping_total),
        "tax_total": str(tax_total),
        "discount_amount": str(discount_amount),
        "grand_total": str(final_total),
        "message": f"Coupon {coupon.code} applied successfully!"
    })

@login_required
@require_POST
def create_discounted_order_ajax(request):
    """
    Create a new Razorpay order after applying a coupon discount.
    """
    import razorpay
    from django.conf import settings

    try:
        data = json.loads(request.body)
        total_after_discount = data.get("total_after_discount")

        # 🟢 Validate total
        if not total_after_discount:
            return JsonResponse({"success": False, "message": "Missing total."})

        try:
            total_value = float(total_after_discount)
        except (TypeError, ValueError):
            return JsonResponse({"success": False, "message": "Invalid total amount."})

        if total_value <= 0:
            return JsonResponse({"success": False, "message": "Total must be greater than zero."})

        # 🟢 Initialize Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        # 🟢 Create new order (in paise)
        razorpay_order = client.order.create({
            "amount": int(total_value * 100),
            "currency": "INR",
            "payment_capture": "1",
        })

        # 🟢 Save order ID to session (optional)
        request.session["razorpay_order_id"] = razorpay_order.get("id")

        return JsonResponse({
            "success": True,
            "order_id": razorpay_order.get("id"),
            "amount": razorpay_order.get("amount"),
        })

    except razorpay.errors.BadRequestError as e:
        return JsonResponse({"success": False, "message": f"Razorpay Error: {str(e)}"})
    except Exception as e:
        print("⚠️ Razorpay order creation error:", e)
        return JsonResponse({"success": False, "message": str(e)})

class CustomSignupView(SignupView):
    template_name = "account/login.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # 🔥 Always tell template we are on signup tab
        ctx["active_tab"] = "signup"
        return ctx

    def form_invalid(self, form):
        """
        This runs when:
        - username already exists
        - email already exists
        - password validation fails
        """
        response = super().form_invalid(form)

        # 🔥 Force signup tab on error
        if hasattr(response, "context_data"):
            response.context_data["active_tab"] = "signup"

        return response

    def get_success_url(self):
        """
        This runs ONLY when signup is successful
        """
        post_next = self.request.POST.get("next")
        get_next = self.request.GET.get("next")

        print("✅ SIGNUP REDIRECT CHECK")
        print("POST next =", post_next)
        print("GET next  =", get_next)

        if post_next:
            return post_next
        if get_next:
            return get_next

        print("✅ No next → redirecting to dashboard")
        return "/account/dashboard/"
                                                                     
def get_or_create_session_key(request):
    """Ensure session_key exists for guest carts."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def merge_guest_cart(user, session_key):
    """Merge guest cart into user's cart after login."""
    try:
        guest_cart = Cart.objects.get(session_key=session_key, user=None)
    except Cart.DoesNotExist:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)

    for item in guest_cart.items.select_related("variant"):
        # 🚫 Skip invalid items (extra safety)
        if not item.variant:
            continue

        cart_item, created = CartItem.objects.get_or_create(
            cart=user_cart,
            product=item.product,
            variant=item.variant,   # ✅ REQUIRED
        )
        if not created:
            cart_item.quantity += item.quantity
        else:
            cart_item.quantity = item.quantity

        cart_item.save()

    guest_cart.delete()

def calculate_cart_totals(cart):
    subtotal = Decimal("0.00")
    shipping_total = Decimal("0.00")
    tax_total = Decimal("0.00")

    if not cart:
        return subtotal, shipping_total, tax_total, subtotal

    for item in cart.items.select_related("variant"):
        qty = item.quantity

        # 🟢 ALWAYS use variant pricing
        if not item.variant:
            continue  # safety guard – no variant, no price

        price = Decimal(item.variant.offer_price or item.variant.price)

        # 🟢 Centralized rules (example)
        shipping_cost = Decimal("0.00")   # free shipping
        tax_amount = price * Decimal("0.18")  # 18% GST

        subtotal += price * qty
        shipping_total += shipping_cost * qty
        tax_total += tax_amount * qty

    grand_total = subtotal + shipping_total + tax_total
    return subtotal, shipping_total, tax_total, grand_total

def cart_view(request):
    session_key = get_or_create_session_key(request)

    # --------- MERGE GUEST CART FOR LOGGED IN USERS ----------
    if request.user.is_authenticated:
        merge_guest_cart(request.user, session_key)
        cart_data = Cart.objects.for_user_or_session(user=request.user)
    else:
        cart_data = Cart.objects.for_user_or_session(session_key=session_key)

    cart_instance = cart_data.get("cart")

    # --------- INITIAL TOTALS (BASE TOTALS BEFORE DISCOUNT) ---------
    subtotal, shipping_total, tax_total, grand_total = calculate_cart_totals(cart_instance)

    # --------- COUPON LOGIC ---------
    coupon_code = request.session.get("selected_coupon")
    applied_coupon = None
    discount_amount = Decimal("0.00")

    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)

            # Validate coupon based on user + subtotal
            if coupon.is_valid(user=request.user, total=subtotal):
                applied_coupon = coupon
                percent = Decimal(str(coupon.discount_percent))
                discount_amount = (subtotal * percent) / Decimal("100")
        except Coupon.DoesNotExist:
            request.session.pop("selected_coupon", None)

    # Apply discount only if coupon valid
    if applied_coupon:
        grand_total = (subtotal - discount_amount) + shipping_total + tax_total

    # --------- COUPON CLEARING RULE ----------
    # After first page reload, coupon must disappear
    if request.session.get("coupon_just_applied", False):
        # Allow 1 page reload to show discount
        request.session["coupon_just_applied"] = False
    else:
        # If user didn't just apply coupon → remove it
        request.session.pop("selected_coupon", None)

    # --------- RENDER CONTEXT ---------
    cart_data.update({
        "cart_items": cart_data.get("items", []),
        "subtotal": subtotal,
        "shipping_total": shipping_total,
        "tax_total": tax_total,
        "discount_amount": discount_amount,
        "grand_total": grand_total,
        "applied_coupon": applied_coupon,
        "saved_items": [],
    })

    return render(request, "store/cart.html", cart_data)

@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    variant_id = request.POST.get("variant_id")

    # ✅ AUTO-SELECT VARIANT IF NOT PROVIDED
    if variant_id:
        variant = ProductVariant.objects.filter(
            id=variant_id,
            product=product
        ).first()
    else:
        # Pick default variant (first / cheapest / in-stock)
        variant = product.variants.order_by("price").first()

    # ❌ If product has variants but none exist (safety check)
    if product.variants.exists() and not variant:
        return JsonResponse(
            {"success": False, "error": "Variant not available"},
            status=400
        )

    try:
        quantity = int(request.POST.get("quantity", 1))
        quantity = max(quantity, 1)
    except (ValueError, TypeError):
        quantity = 1

    session_key = get_or_create_session_key(request)

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        cart, _ = Cart.objects.get_or_create(
            session_key=session_key,
            user=None
        )

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,  # ✅ ALWAYS SET
        defaults={"quantity": quantity}
    )

    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    subtotal, shipping_total, tax_total, grand_total = calculate_cart_totals(cart)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "success": True,
            "cart_count": cart.items.aggregate(total=Sum("quantity"))["total"] or 0,
            "item_total": str(cart_item.total_price),
            "subtotal": str(subtotal),
            "shipping_total": str(shipping_total),
            "tax_total": str(tax_total),
            "grand_total": str(grand_total),
        })

    return redirect("cart")

@require_POST
def update_cart(request, item_id):
    # find cart_item for user or guest
    if request.user.is_authenticated:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    else:
        session_key = get_or_create_session_key(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart__session_key=session_key, cart__user=None)

    action = request.POST.get("action")
    quantity = request.POST.get("quantity")

    if action == "increase":
        cart_item.quantity += 1
    elif action == "decrease" and cart_item.quantity > 1:
        cart_item.quantity -= 1
    elif quantity is not None:
        try:
            q = int(quantity)
            if q > 0:
                cart_item.quantity = q
            else:
                # delete item and return updated totals
                cart = cart_item.cart
                cart_item.delete()
                subtotal, shipping_total, tax_total, grand_total = calculate_cart_totals(cart)
                return JsonResponse({
                    "success": True,
                    "item_total": "0.00",
                    "subtotal": str(subtotal),
                    "shipping_total": str(shipping_total),
                    "tax_total": str(tax_total),
                    "grand_total": str(grand_total),
                    "cart_count": cart.total_items,
                })
        except (ValueError, TypeError):
            pass

    cart_item.save()
    cart = cart_item.cart
    subtotal, shipping_total, tax_total, grand_total = calculate_cart_totals(cart)

    return JsonResponse({
        "success": True,
        "item_total": str(cart_item.total_price),
        "subtotal": str(subtotal),
        "shipping_total": str(shipping_total),
        "tax_total": str(tax_total),
        "grand_total": str(grand_total),
        "cart_count": cart.total_items,
    })


@require_POST
def remove_from_cart(request, item_id):
    if request.user.is_authenticated:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    else:
        session_key = get_or_create_session_key(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart__session_key=session_key, cart__user=None)

    cart = cart_item.cart
    cart_item.delete()

    subtotal, shipping_total, tax_total, grand_total = calculate_cart_totals(cart)

    return JsonResponse({
        "success": True,
        "item_total": "0.00",
        "subtotal": str(subtotal),
        "shipping_total": str(shipping_total),
        "tax_total": str(tax_total),
        "grand_total": str(grand_total),
        "cart_count": cart.total_items,
    })

@login_required
def save_for_later(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product = cart_item.product

    # Create or ignore duplicate saved items
    SavedItem.objects.get_or_create(user=request.user, product=product)

    # Remove from cart
    cart_item.delete()

    return JsonResponse({
        "success": True,
        "product": {
            "id": product.id,
            "name": product.name,
            "image": product.get_main_image_url(),
            "price": float(product.price),
        }
    })

@login_required
def move_to_cart(request, product_id):
    saved_item = get_object_or_404(
        SavedItem,
        user=request.user,
        product_id=product_id
    )

    cart, _ = Cart.objects.get_or_create(user=request.user)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=saved_item.product,
        variant=saved_item.variant,   # ✅ REQUIRED
        defaults={"quantity": 1},
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    saved_item.delete()

    return JsonResponse({"success": True})

def fetch_products(request):
    sort = request.GET.get('sort')
    category_ids = request.GET.get('category', '').split(',') if request.GET.get('category') else []
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    products = Product.objects.all()

    # Filters
    if category_ids:
        products = products.filter(category__id__in=category_ids)
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Sorting
    if sort == 'newest':
        products = products.order_by('-id')
    elif sort == 'low-high':
        products = products.order_by('price')
    elif sort == 'high-low':
        products = products.order_by('-price')
    elif sort == 'rating':
        products = products.order_by('-avg_rating')

    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)

    return render(request, 'partials/product_section.html', {
        'products': page_obj.object_list,
        'has_next_page': page_obj.has_next(),
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
    })

def faq_view(request):
    """
    Enhanced FAQ view with optional search suggestions and 
    future-ready data for chat/contact widgets.
    """
    query = request.GET.get('q', '').strip()
    faqs = FAQ.objects.all()

    # If user typed a search query — filter FAQs
    if query:
        faqs = faqs.filter(question__icontains=query) | faqs.filter(answer__icontains=query)

    # Pass extra context for animations & chat widget
    context = {
        'faqs': faqs,
        'query': query,
        'has_search': bool(query),
        'whatsapp_number': '+919876543210',  # <-- replace with your business number
        'contact_email': 'support@myshop.com',  # <-- optional
    }

    return render(request, 'store/faq.html', context)

def download_invoice(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    items = order.items.all()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=invoice_{order.id}.pdf"

    p = canvas.Canvas(response, pagesize=A4)

    y = 800
    p.setFont("Helvetica-Bold", 16)
    p.drawString(40, y, f"Invoice - Order #{order.id}")
    y -= 40

    p.setFont("Helvetica", 12)
    for item in items:
        p.drawString(40, y, f"{item.product.name} (x{item.quantity}) - ₹{item.total_price}")
        y -= 25

    p.drawString(40, y - 20, f"Total: ₹{order.total_price}")

    p.showPage()
    p.save()

    return response

def download_receipt(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)

    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{payment.id}.pdf"'

    # PDF canvas
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    y = height - 50
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, y, "Payment Receipt")

    y -= 40
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Receipt ID: {payment.id}")

    y -= 20
    p.drawString(50, y, f"Transaction ID: {payment.transaction_id or 'N/A'}")

    y -= 20
    p.drawString(50, y, f"Status: {payment.status}")

    y -= 20
    created = payment.created_at.strftime("%d %b %Y, %I:%M %p") if payment.created_at else "N/A"
    p.drawString(50, y, f"Created At: {created}")

    y -= 20
    completed = payment.completed_at.strftime("%d %b %Y, %I:%M %p") if payment.completed_at else "N/A"
    p.drawString(50, y, f"Completed At: {completed}")

    y -= 20
    p.drawString(50, y, f"Amount: ₹{payment.amount if hasattr(payment, 'amount') else 'N/A'}")

    # Footer
    y -= 40
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, y, "-- Thank you for shopping with MFY Store --")

    p.showPage()
    p.save()

    return response

def track_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    delivery = order.delivery_progress

    context = {
        "order": order,
        "placed": delivery >= 5,
        "processing": delivery >= 40,
        "shipped": delivery >= 60,
        "out_for_delivery": delivery >= 85,
        "delivered": delivery >= 100,
    }

    return render(request, "store/track_order.html", context)

def request_return(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "store/return_request.html", {"order": order})

def return_detail(request, return_id):
    ret = get_object_or_404(ReturnRequest, id=return_id, user=request.user)
    return render(request, "store/return_detail.html", {"return_obj": ret})

def subscribe_newsletter(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if not email:
            messages.error(request, "Please enter a valid email.")
            return redirect("offers")

        # Save email if not already subscribed
        subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)

        if created:
            messages.success(request, "You are subscribed! 🎉")
        else:
            messages.info(request, "You’re already subscribed.")

        return redirect("offers")

def grab_offer(request, coupon_id):
    from store.models import Coupon  # import if coupon in store app

    try:
        coupon = Coupon.objects.get(id=coupon_id, is_active=True)
    except Coupon.DoesNotExist:
        messages.error(request, "Offer no longer available.")
        return redirect("offers")

    # save coupon code in session
    request.session["selected_coupon"] = coupon.code
    request.session["coupon_just_applied"] = True

    messages.success(request, f"{coupon.code} applied successfully!")

    # redirect to cart
    return redirect("cart")

def remove_coupon(request):
    if request.method == "POST":
        request.session.pop("selected_coupon", None)

        return JsonResponse({
            "success": True,
        })

    return JsonResponse({"success": False}, status=400)

