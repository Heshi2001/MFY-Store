from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Cart, Order, OrderItem, ProductVariant, ProductImage, Wishlist, Review
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from .forms import ContactForm, ReviewForm
import json

def index(request):
    query = request.GET.get('q')
    if query:
        products = Product.objects.filter(name__icontains=query)
    else:
        products = Product.objects.all().order_by('-id')[:6]  # Latest 6

    for product in products:
        product.first_image = product.images.first()  # Show only first image

    return render(request, 'store/index.html', {'products': products})

def products_view(request):
    products = Product.objects.prefetch_related('images').order_by('-id')

    for product in products:
        product.first_image = product.images.first()  # Used for showing image

    return render(request, 'store/products.html', {
        "products": products
    })

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
   
    wishlist_product_ids = list(
        Wishlist.objects.filter(user=request.user if request.user.is_authenticated else None)
        .values_list('product_id', flat=True)
    )

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
