from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Cart, Order, OrderItem, ProductVariant, ProductImage, Wishlist, Review, UserProfile, Address, Coupon
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth import login
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from .forms import ContactForm, ReviewForm, UserUpdateForm
from django.contrib.auth.models import User
from .models import EmailOTP
import json
import random
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import get_user_model
from allauth.account.views import LoginView
from allauth.account.forms import SignupForm
from .forms import AddressForm
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth import update_session_auth_hash
from django.urls import reverse_lazy

User = get_user_model()

def index(request):
    query = request.GET.get('q')
    if query:
        products = Product.objects.filter(name__icontains=query)
    else:
        products = Product.objects.all().order_by('-id')[:6]  # Latest 6

    for product in products:
        product.first_image = product.images.first()  # Show only first image

    return render(request, 'store/index.html', {'products': products})

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
        product.first_image = product.images.first()  # Used for showing image

    return render(request, 'store/products.html', {
        "products": products
    })

@login_required
def orders_list(request):
    # later you can fetch real orders for the logged-in user
    orders = []  
    return render(request, "account/orders.html", {"orders": orders})

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variants = product.variants.all()
    main_images = product.images.filter(is_main=True)
    reviews = Review.objects.filter(product=product).order_by('-id')
    sizes = list(dict.fromkeys(
        [variant.size for variant in variants if variant.size is not None]
    ))
    colors = list(dict.fromkeys(
        [variant.color for variant in variants if variant.color is not None]
    ))

    first_image_url =  main_images.first().image.url if main_images.exists() else ""
   
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
        'form': ReviewForm()
    }
    return render(request, 'store/product_detail.html', context)


def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user if request.user.is_authenticated else None, product=product)
    return redirect('wishlist')

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
def add_to_cart(request, product_id):
    product = Product.objects.get(id=product_id)
    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
    if not created:
        cart_item.quantity += 1
    cart_item.save()
    return redirect('index')

@login_required
def view_cart(request):
    cart_items = Cart.objects.filter(user=request.user)
    return render(request, 'store/cart.html', {'cart_items': cart_items})

@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user)
    if not cart_items:
        return redirect('view_cart')

    total_price = sum(item.product.price * item.quantity for item in cart_items)

    order = Order.objects.create(
        user=request.user,
        total_price=total_price,
        created_at=timezone.now(),
        payment_id='COD'
    )

    for item in cart_items:
        if item.product.stock < item.quantity:
            return render(request, 'store/out_of_stock.html', {'product': item.product})

        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )

        item.product.stock -= item.quantity
        item.product.save()

    cart_items.delete()

    return render(request, 'store/invoice.html', {'order': order})

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

def search_view(request):
    query = request.GET.get('query')
    products = []
    if query:
        products = Product.objects.filter(name__icontains=query)

    return render(request, 'store/search_results.html', {'products': products, 'query': query})

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
    if request.method == "POST":
        email = request.POST.get("email")

        # Check if email exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No account found with this email.")
            return redirect("account_login")

        # Generate OTP
        otp = str(random.randint(100000, 999999))

        # Save OTP in DB (delete old ones first)
        EmailOTP.objects.filter(user=user).delete()
        EmailOTP.objects.create(user=user, otp=otp)

        # Send OTP via email
        try:
             send_mail(
                subject="Your OTP Code",
                message=f"Your OTP code is {otp}",
                from_email="euliheshicleetus2001@gmail.com",
                recipient_list=[email],
            )
        except Exception as e:
            messages.error(request, "Unable to send OTP email. Please try again later.")
            return redirect("account_login")     

        # Store user_id in session for verification step
        request.session["otp_user_id"] = user.id

        messages.success(request, "OTP sent to your email.")
        return redirect("verify_email_otp")   # ✅ go to OTP verification page

    return redirect("account_login")

def verify_email_otp(request):
    if request.method == "POST":
        otp_entered = request.POST.get("otp")
        user_id = request.session.get("otp_user_id")

        if not user_id:
            messages.error(request, "Session expired. Please request OTP again.")
            return redirect("otp_login")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect("otp_login")

        try:
            otp_obj = EmailOTP.objects.get(user=user, otp=otp_entered)
        except EmailOTP.DoesNotExist:
            messages.error(request, "Invalid OTP.")
            return render(request, "store/verify_otp.html")

        # Check if expired
        if otp_obj.is_expired():
            otp_obj.delete()
            messages.error(request, "OTP expired. Please request again.")
            return redirect("otp_login")

        # ✅ Valid OTP
        otp_obj.delete()  # remove after use
        login(request, user)
        del request.session["otp_user_id"]

        messages.success(request, "OTP verified successfully. You are now logged in.")
        return redirect("otp_success")

    return render(request, "store/verify_otp.html")

def otp_success(request):
    return render(request, "store/verify_email_otp.html")

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
