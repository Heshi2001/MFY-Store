from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Cart, Order, OrderItem, ProductVariant, ProductImage, Wishlist, Review, UserProfile, Address, Coupon, CartItem, Category, Banner, HomeSection, PromoBanner
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

logger = logging.getLogger(__name__)

User = get_user_model()

def index(request):
    query = request.GET.get('q')
    if query:
        products = Product.objects.filter(name__icontains=query)
    else:
        products = Product.objects.all().order_by('-id')[:6]

    # Prepare product images & discount logic
    for product in products:
        if getattr(product, 'image_mode', None) == "custom" and getattr(product, 'custom_image', None):
            product.first_image = product.custom_image
        else:
            product.first_image = getattr(product, 'images', None).first() if hasattr(product, 'images') else None

        if getattr(product, 'offer_price', None) and product.offer_price < product.price:
            product.discount_percent = round(
                ((product.price - product.offer_price) / product.price) * 100
            )
        else:
            product.discount_percent = None

    # ✅ Categories
    top_categories = Category.objects.filter(parent__isnull=True)  # homepage circles
    categories_with_children = Category.objects.filter(parent__isnull=True).prefetch_related('children')  # sidebar recursion

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
    
    # ✅ Dynamic Homepage Sections (MPTT optimized)
    home_sections = HomeSection.objects.filter(active=True).order_by('order')
    dynamic_sections = []

    for section in home_sections:
        if section.category:
            # Use MPTT to include the category itself + all nested subcategories
            section_products = Product.objects.filter(
                category__in=section.category.get_descendants(include_self=True)
            ).prefetch_related('images').order_by('-id')[:section.product_limit]
        else:
            section_products = Product.objects.all().order_by('-id')[:section.product_limit]

        # Prepare image and discount details (same logic as your main product loop)
        for product in section_products:
            if getattr(product, 'image_mode', None) == "custom" and getattr(product, 'custom_image', None):
                product.first_image = product.custom_image
            else:
                product.first_image = getattr(product, 'images', None).first() if hasattr(product, 'images') else None

            if getattr(product, 'offer_price', None) and product.offer_price < product.price:
                product.discount_percent = round(
                    ((product.price - product.offer_price) / product.price) * 100
                )
            else:
                product.discount_percent = None

        dynamic_sections.append({
            "title": section.title,
            "products": section_products,
        })

    # ✅ Wishlist
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    # ✅ Cart count
    if request.user.is_authenticated:
        cart_data = Cart.objects.for_user_or_session(user=request.user)
    else:
        session_key = get_or_create_session_key(request)
        cart_data = Cart.objects.for_user_or_session(session_key=session_key)

    cart_items_count = cart_data["cart"].items.aggregate(total=Sum("quantity"))["total"] or 0
      
    return render(request, 'store/index.html', {
        'products': products,
        'categories': top_categories,
        'sidebar_categories': categories_with_children,
        'banners': banners,
        'wishlist_ids': wishlist_ids,
        'cart_items_count': cart_items_count,
        'dynamic_sections': dynamic_sections,
        'promo_banner_text': promo_banner_text,
    })
def category_products(request, slug):
    # SEO-friendly category page
    category = get_object_or_404(Category, slug=slug)

    # Get all descendant categories including the current one
    descendants = category.get_descendants(include_self=True)
    descendant_ids = [c.id for c in descendants]

    # Fetch all products in this category or its subcategories
    products = Product.objects.filter(category__id__in=descendant_ids).distinct()

    # Handle product image + discount display
    for product in products:
        if getattr(product, 'image_mode', None) == "custom" and getattr(product, 'custom_image', None):
            product.first_image = product.custom_image
        else:
            product.first_image = getattr(product, 'images', None).first() if hasattr(product, 'images') else None

        if getattr(product, 'offer_price', None) and product.offer_price < product.price:
            product.discount_percent = round(
                ((product.price - product.offer_price) / product.price) * 100
            )
        else:
            product.discount_percent = None

    # Get cart item count
    if request.user.is_authenticated:
        cart_data = Cart.objects.for_user_or_session(user=request.user)
    else:
        session_key = get_or_create_session_key(request)
        cart_data = Cart.objects.for_user_or_session(session_key=session_key)

    cart_items_count = cart_data["cart"].items.aggregate(total=Sum("quantity"))["total"] or 0

    return render(request, 'store/category_products.html', {
        'category': category,
        'products': products,
        'cart_items_count': cart_items_count,
    })

@login_required
def account_dashboard(request):
    # Ensure user has a profile
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Fetch related data
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    wishlist = Wishlist.objects.filter(user=request.user)
    user_coupons = Coupon.objects.filter(users=request.user, is_active=True)

    context = {
        "profile": profile,
        "addresses": addresses,
        "orders": orders,
        "wishlist": wishlist,
        "user_coupons": user_coupons,
    }

    return render(request, "account/dashboard.html", context)


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
def address_add(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            # ✅ Sync names into User model
            if address.first_name and address.last_name:
                request.user.first_name = address.first_name
                request.user.last_name = address.last_name
                request.user.save()

            return redirect("account_addresses")  # redirect to address list
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
def delete_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        address.delete()
        return redirect("account_addresses")
    return render(request, "account/address_confirm_delete.html", {"address": address})

def products_view(request):
    products = Product.objects.prefetch_related('images').order_by('-id')

    for product in products:
        # Use custom_image if image_mode=custom
        if product.image_mode == "custom" and product.custom_image:
            product.first_image = product.custom_image
        else:
            product.first_image = product.images.first()  # fallback
         # Calculate discount if applicable
        if product.offer_price and product.offer_price < product.price:
            product.discount_percent = round(
                ((product.price - product.offer_price) / product.price) * 100
            )
        else:
            product.discount_percent = None
    
    return render(request, 'store/products.html', {
        "products": products,
    })

@login_required
def orders_list(request):
    """
    Show all orders for the logged-in user.
    Orders are sorted with the newest first.
    """
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "account/orders.html", {"orders": orders})

@login_required
def order_detail(request, order_id):
    """
    Show details of a single order (items, status, price).
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.items.select_related("product").all()

    return render(request, "account/order_detail.html", {
        "order": order,
        "items": items,
    })

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variants = product.variants.all()
    main_images = product.images.filter(is_main=True)

    # Use custom_image if image_mode=custom
    if product.image_mode == "custom" and product.custom_image:
        first_image_url = product.custom_image.url
    else:
        first_image_url = main_images.first().image.url if main_images.exists() else ""

    reviews = Review.objects.filter(product=product).order_by('-id')
    sizes = list(dict.fromkeys(
        [variant.size for variant in variants if variant.size is not None]
    ))
    colors = list(dict.fromkeys(
        [variant.color for variant in variants if variant.color is not None]
    ))

    variant_map = json.dumps([
        {
            "color": variant.color.id if variant.color else None,
            "image_url": variant.image.url if variant.image else first_image_url
        }
        for variant in variants
    ])

    if request.user.is_authenticated:
        wishlist_product_ids = list(
            Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
        )
    else:
        wishlist_product_ids = []

    recommended_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]

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
        'first_image_url': first_image_url,  # pass to template for default display
    }
    return render(request, 'store/product_detail.html', context)

@method_decorator(cache_page(60*5), name="list")
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all().prefetch_related("images", "variants__color", "variants__size").select_related("category")
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["dealer", "category__id", "category__name", "sku"]
    search_fields = ["name", "description", "sku"]
    ordering_fields = ["price", "name", "stock"]
    ordering = ["name"]

@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)

    # If it already exists, remove it (toggle)
    if not created:
        wishlist_item.delete()
        return JsonResponse({'added': False})

    # If added new
    return JsonResponse({'added': True})

def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=request.user if request.user.is_authenticated else None, product=product).delete()
    return redirect('wishlist')

def wishlist_view(request):
    user = request.user if request.user.is_authenticated else None
    wishlist_items = Wishlist.objects.filter(user=user)
    return render(request, 'store/wishlist.html', {'wishlist_items': wishlist_items})

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
    """
    Checkout page – creates Razorpay order and passes it to template.
    """
    cart_data = Cart.objects.for_user_or_session(
        user=request.user, session_key=request.session.session_key
    )
    cart = cart_data["cart"]
    items = cart_data["items"]

    if not items:
        return redirect("view_cart")

    addresses = Address.objects.filter(user=request.user)
    coupon_code = request.GET.get("coupon") or request.POST.get("coupon")
    discount = 0

    # 🟢 Coupon handling
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            if coupon.is_valid():
                discount = coupon.discount_percent
                coupon.users.add(request.user)
            else:
                messages.error(request, "Invalid or expired coupon.")
        except Coupon.DoesNotExist:
            messages.error(request, "Coupon not found.")

    # 🟢 Total price after discount
    total_price = cart.total_price
    if discount:
        total_price = total_price - (total_price * discount / 100)

    # 🟢 Create Razorpay order
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    razorpay_order = client.order.create({
        "amount": int(total_price * 100),  # in paise
        "currency": "INR",
        "payment_capture": "1",
    })

    # Save order_id temporarily in session
    request.session["razorpay_order_id"] = razorpay_order["id"]

    return render(request, "store/checkout.html", {
        "cart": cart,
        "items": items,
        "addresses": addresses,
        "total_price": total_price,
        "discount": discount,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "razorpay_order": razorpay_order,
    })


@csrf_exempt
@login_required
def payment_success(request):
    """
    Razorpay callback – verifies signature, creates dealer/self orders,
    reduces stock, clears cart, and triggers external dealer APIs.
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
                return JsonResponse({"success": False, "error": "Cart empty"})

            address_id = request.session.get("checkout_address_id")
            shipping_address = Address.objects.filter(id=address_id, user=request.user).first()

            # 🟢 Create dealer-wise orders
            dealer_orders = {}
            for item in items:
                dealer = getattr(item.product, "dealer", "Self")  # default Self

                if dealer not in dealer_orders:
                    dealer_orders[dealer] = Order.objects.create(
                        user=request.user,
                        total_price=0,
                        payment_id=data["razorpay_order_id"],  # link with Razorpay order
                        shipping_address=shipping_address,
                        billing_address=shipping_address,
                        status="Paid",
                    )

                order = dealer_orders[dealer]

                # Out of stock check for self-fulfilled
                if item.product.stock < item.quantity and dealer == "Self":
                    return render(request, "store/out_of_stock.html", {"product": item.product})

                # Create order item
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    variant=item.variant,
                    quantity=item.quantity,
                    price=item.product.offer_price or item.product.price,
                )

                order.total_price += (item.product.offer_price or item.product.price) * item.quantity
                order.save()

                # Reduce stock for self-fulfilled
                if dealer == "Self":
                    item.product.stock -= item.quantity
                    item.product.save()

                # 🟢 API calls for Qikink / Printrove
                if dealer == "Qikink":
                    from store.qikink_api import create_test_order
                    response = create_test_order(order)
                    print("Qikink response:", response)
                elif dealer == "Printrove":
                    # TODO: Replace with real Printrove API
                    print(f"Send order {order.id} to Printrove API")

            # 🟢 Clear cart
            cart.items.all().delete()

            return JsonResponse({"success": True})

        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({"success": False, "error": "Payment verification failed"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})

def order_success(request):
    return render(request, "store/order_success.html")

def about(request):
    context = {
        'site_title': 'Sixteen Clothing',
        'about_text': "We are passionate about fashion and committed to quality. Our goal is to bring elegant, affordable styles to everyone.",
        'social_links': [
            {'url': 'https://facebook.com', 'icon_class': 'fa-facebook'},
            {'url': 'https://instagram.com', 'icon_class': 'fa-instagram'},
            {'url': 'mailto:example@gmail.com','icon_class': 'fa-envelope'},
            {'url': 'https://wa.me/919876543210', 'icon_class': 'fa-whatsapp'},
        ],
        'team_members': [
            {
                'name': 'Alice Johnson',
                'role': 'Founder & CEO',
                'description': 'Leads the creative and strategic direction of the company.',
                'image': 'static/store/images/team1.jpg',
                'social_links': [
                    {'url': 'https://linkedin.com/in/alice', 'icon_class': 'fa-linkedin'},
                    {'url': '#', 'icon_class': 'fa-twitter'}
                ]
            },
            {
                'name': 'Bob Smith',
                'role': 'Product Manager',
                'description': 'Oversees production and product development.',
                'image': 'store/images/team2.jpg',
                'social_links': [
                    {'url': 'https://linkedin.com/in/bob', 'icon_class': 'fa-linkedin'}
                ]
            },
            {
                'name': 'Catherine Lee',
                'role': 'Marketing Head',
                'description': 'Manages brand communication and marketing campaigns.',
                'image': 'store/images/team3.jpg',
                'social_links': [
                    {'url': '#', 'icon_class': 'fa-facebook'}
                ]
            }
        ],
        'services': [
            {
                'icon': 'fa-truck',
                'title': 'Fast Delivery',
                'description': 'We ensure quick and safe delivery of your orders.',
                'link': '#',
                'button_text': 'Learn More'
            },
            {
                'icon': 'fa-tags',
                'title': 'Affordable Prices',
                'description': 'Fashion doesn’t have to be expensive.',
                'link': '#',
                'button_text': 'Shop Now'
            },
            {
                'icon': 'fa-thumbs-up',
                'title': 'Quality Guaranteed',
                'description': 'Only the best materials and craftsmanship.',
                'link': '#',
                'button_text': 'Discover'
            }
        ],
        'clients': [
            {'image': 'store/images/client-01.png'},
            {'image': 'store/images/client-02.png'},
            {'image': 'store/images/client-03.png'},
            {'image': 'store/images/client-04.png'},
            {'image': 'store/images/client-05.png'}
        ]
    }
    return render(request, 'store/about.html', context)

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            send_mail(
                subject=contact.subject,
                message=contact.message,
                from_email=contact.email,
                recipient_list=['euliheshicleetus2001@gmail.com'],
                fail_silently=False,
            )
            return redirect('contact_thanks')
    else:
        form = ContactForm()
    return render(request, 'store/contact.html', {'form': form})

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
            products = products.order_by('offer_price')
        elif sort == 'price_desc':
            products = products.order_by('-offer_price')
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
            products = products.order_by('offer_price')
        elif sort == 'price_desc':
            products = products.order_by('-offer_price')
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

def faq(request):
    return render(request, 'store/faq.html')

class CombinedLoginView(LoginView):
    template_name = "account/login.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            ctx["signup_form"] = SignupForm()
        except Exception:
            ctx["signup_form"] = None
        return ctx

   
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
        return redirect("account_login")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        messages.error(request, "No account found with this email.")
        return redirect("account_login")

    otp = f"{random.randint(100000, 999999)}"

    try:
        # Remove any old OTPs for this user and create a new one
        EmailOTP.objects.filter(user=user).delete()
        EmailOTP.objects.create(user=user, otp=otp)
    except Exception as e:
        logger.exception("Failed to save OTP to DB for %s", email)
        messages.error(request, "Server error. Please try again shortly.")
        return redirect("account_login")

    # Attempt to send email
    try:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.EMAIL_HOST_USER
        send_mail(
            subject="Your OTP Code",
            message=f"Your OTP code is {otp}",
            from_email=from_email,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        logger.exception("Failed to send OTP email to %s", email)
        messages.error(request, "Unable to send OTP email. Please try again later.")
        return redirect("account_login")

    # Save the user id in session for verification step
    request.session["otp_user_id"] = user.id
    # Optionally set expiry for session key (session cookie expiry already set in settings)
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
    logger.info("otp_success view hit. User: %s authenticated=%s", getattr(request.user, 'email', None), request.user.is_authenticated)
    return render(request, "store/otp_success.html")

@login_required
def payments(request):
    # later you can integrate with real payment models
    return render(request, "account/payments.html")

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
    coupons = Coupon.objects.filter(users=request.user, is_active=True)
    return render(request, "account/offers.html", {
        "coupons": coupons
    })

class CustomSignupView(SignupView):
    template_name = "account/login.html"
                                                                      
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

    for item in guest_cart.items.all():
        cart_item, created = CartItem.objects.get_or_create(
            cart=user_cart, product=item.product
        )
        if not created:
            cart_item.quantity += item.quantity
        cart_item.save()

    guest_cart.delete()


def cart_view(request):
    session_key = get_or_create_session_key(request)

    if request.user.is_authenticated:
        merge_guest_cart(request.user, session_key)
        cart_data = Cart.objects.for_user_or_session(user=request.user)
    else:
        cart_data = Cart.objects.for_user_or_session(session_key=session_key)

    # Assign first_image for each cart item product
    for item in cart_data.get("items", []):
        product = item.product
        if product.image_mode == "custom" and product.custom_image:
            product.first_image = product.custom_image
        else:
            product.first_image = product.images.first()  # fallback
    cart_data["cart_items"] = cart_data.get("items", [])

    return render(request, "store/cart.html", cart_data)

@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variant_id = request.POST.get("variant_id")
    variant = ProductVariant.objects.filter(id=variant_id).first() if variant_id else None
    quantity = int(request.POST.get("quantity", 1))

    session_key = get_or_create_session_key(request)

    if request.user.is_authenticated:
        cart_data = Cart.objects.for_user_or_session(user=request.user)
    else:
        cart_data = Cart.objects.for_user_or_session(session_key=session_key)

    cart = cart_data["cart"]

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        defaults={"quantity": quantity}
    )
    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "success": True,
            "cart_count": cart.items.aggregate(total=Sum("quantity"))["total"] or 0,
            "item_total": cart_item.total_price,
            "subtotal": cart.total_price,
            "total": cart.total_price,
        })

    return redirect("cart")

@require_POST
def update_cart(request, item_id):
    """Update or remove a cart item (AJAX)."""
    if request.user.is_authenticated:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    else:
        session_key = get_or_create_session_key(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart__session_key=session_key)

    action = request.POST.get("action")
    quantity = request.POST.get("quantity")

    # ✅ Handle increase/decrease buttons
    if action == "increase":
        cart_item.quantity += 1
    elif action == "decrease" and cart_item.quantity > 1:
        cart_item.quantity -= 1
    # ✅ Handle direct input field
    elif quantity is not None:
        quantity = int(quantity)
        if quantity > 0:
            cart_item.quantity = quantity
        else:
            cart_item.delete()
            cart = cart_item.cart
            return JsonResponse({
                "success": True,
                "item_total": 0,
                "subtotal": cart.total_price,
                "total": cart.total_price,
                "cart_count": cart.items.aggregate(total=Sum("quantity"))["total"] or 0,
            })

    cart_item.save()
    cart = cart_item.cart

    return JsonResponse({
        "success": True,
        "item_total": cart_item.total_price,
        "subtotal": cart.total_price,
        "total": cart.total_price,
        "cart_count": cart.items.aggregate(total=Sum("quantity"))["total"] or 0,
    })

@require_POST
def remove_from_cart(request, item_id):
    """Remove item from cart (AJAX)."""
    if request.user.is_authenticated:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    else:
        session_key = get_or_create_session_key(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart__session_key=session_key)

    cart = cart_item.cart
    cart_item.delete()

    return JsonResponse({
        "success": True,
        "item_total": 0,
        "subtotal": cart.total_price,
        "total": cart.total_price,
        "cart_count": cart.items.aggregate(total=Sum("quantity"))["total"] or 0,
    })

