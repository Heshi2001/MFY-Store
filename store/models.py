from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField
from django.utils import timezone
from datetime import timedelta
from mptt.models import MPTTModel, TreeForeignKey
from django.utils.text import slugify

class Category(MPTTModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True, null=True)
    image = CloudinaryField('image', blank=True, null=True)

    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-generate slug if not set
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"/category/{self.slug}/"

    @property
    def has_children(self):
        return self.get_children().exists()
 
class Product(models.Model):
    DEALER_CHOICES = [
        ("Self", "Self-Fulfilled"),
        ("Qikink", "Qikink"),
        ("Printrove", "Printrove"),
    ]

    IMAGE_MODE_CHOICES = [
        ("qikink", "Qikink Image"),
        ("custom", "Custom Image"),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    sku = models.CharField(max_length=100, unique=True, null=True, blank=True)  # 🟢 NEW FIELD
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    material = models.CharField(max_length=100, blank=True, null=True)
    rating = models.IntegerField(default=5)
    stock = models.PositiveIntegerField(default=0)
    dealer = models.CharField(max_length=20, choices=DEALER_CHOICES, default="Self")  # 🟢 NEW FIELD
     # 🟢 NEW FIELDS
    image_mode = models.CharField(
        max_length=20,
        choices=IMAGE_MODE_CHOICES,
        default="qikink"
    )
    custom_image = CloudinaryField("custom_image", blank=True, null=True)
    
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, editable=False)

    def save(self, *args, **kwargs):
        """Auto-calculate discount percent when offer_price < price"""
        if self.offer_price and self.offer_price < self.price:
            self.discount_percent = round(((self.price - self.offer_price) / self.price) * 100, 2)
        else:
            self.discount_percent = 0.00
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_dealer_display()})"
   
    def get_main_image_url(self):
        """Return correct image based on mode (custom or qikink)."""
        if self.image_mode == "custom" and self.custom_image:
            return self.custom_image.url
        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image.image.url
        fallback_image = self.images.first()
        if fallback_image:
            return fallback_image.image.url
        return "/static/store/images/placeholder.png"

class Color(models.Model):
    name = models.CharField(max_length=30)
    hex_code = models.CharField(max_length=7)
    image = CloudinaryField("image", blank=True, null=True)

    def __str__(self):
        return self.name


class Size(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    color = models.ForeignKey(Color, on_delete=models.CASCADE, null=True, blank=True)
    size = models.ForeignKey(Size, on_delete=models.CASCADE, null=True, blank=True)
    age_group = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.PositiveIntegerField(blank=True, null=True)
    image = CloudinaryField("image", blank=True, null=True)  # Variant-specific image

    def __str__(self):
        parts = [self.product.name]
        if self.color:
            parts.append(self.color.name)
        if self.size:
            parts.append(self.size.name)
        return " - ".join(parts)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = CloudinaryField("image")
    is_main = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.product.name}"


# ----------------------
# User & Address
# ----------------------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_image = models.ImageField(upload_to="profiles/", blank=True, null=True)

    def __str__(self):
        return self.user.username


class Address(models.Model):
    ADDRESS_TYPES = (
        ("shipping", "Shipping"),
        ("billing", "Billing"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="India")
    postal_code = models.CharField(max_length=30)
    address_type = models.CharField(max_length=30, choices=ADDRESS_TYPES, default="shipping")
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name}, {self.city} ({self.address_type})"


# ----------------------
# Wishlist & Cart
# ----------------------
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_user_product_wishlist")
        ]

    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.product.name}"
        return f"Anonymous - {self.product.name}"

class CartManager(models.Manager):
    def for_user_or_session(self, user=None, session_key=None):
        """
        Return a cart for a logged-in user or guest session.
        If user is logged in, get/create their cart.
        If guest, get/create cart using session_key.
        """
        if user and user.is_authenticated:
            # Pick the latest cart if multiple exist
            cart = self.filter(user=user).order_by('-created_at').first()
            if not cart:
                cart = self.create(user=user)

            # Merge guest cart if session exists
            if session_key:
                guest_cart = self.filter(session_key=session_key).first()
                if guest_cart:
                    for item in guest_cart.items.all():
                        cart_item, created = CartItem.objects.get_or_create(
                            cart=cart,
                            product=item.product
                        )
                        if not created:
                            cart_item.quantity += item.quantity
                        cart_item.save()
                    guest_cart.delete()

        elif session_key:
            cart = self.filter(session_key=session_key).first()
            if not cart:
                cart = self.create(session_key=session_key)
        else:
            raise ValueError("Either user or session_key must be provided.")

        items = cart.items.select_related("product").all()
        return {
            "cart": cart,
            "items": items,
            "cart_total": cart.total_price,
            "cart_count": cart.distinct_items,
            "cart_quantity": cart.total_items,
        }

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="carts", null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CartManager()  # custom manager

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_user_cart')
        ]

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.username}"
        return f"Guest Cart ({self.session_key})"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def distinct_items(self):
        """Return distinct product count (e.g. product A + product B = 2)."""
        return self.items.count()

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product", "variant"], name="unique_cart_product_variant")
        ]

    def __str__(self):
        parts = [self.product.name]
        if self.variant:
            if self.variant.color:
                parts.append(self.variant.color.name)
            if self.variant.size:
                parts.append(self.variant.size.name)
        return f"{' - '.join(parts)} (x{self.quantity})"

    @property
    def total_price(self):
        price = self.product.offer_price if self.product.offer_price else self.product.price
        return price * self.quantity

# ----------------------
# Orders
# ----------------------

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_id = models.CharField(max_length=255)
    order_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Shipped", "Shipped"), ("Delivered", "Delivered")],
        default="Pending",
    )

    shipping_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True, related_name="shipping_orders"
    )
    billing_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_orders"
    )
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    dealer = models.CharField(  # 🟢 NEW FIELD (copied from Product at order time)
        max_length=20,
        choices=Product.DEALER_CHOICES,
        default="Self"
    )

    @property
    def total_price(self):
        return self.price * self.quantity

    def __str__(self):
        parts = [self.product.name]
        if self.variant:
            if self.variant.color:
                parts.append(self.variant.color.name)
            if self.variant.size:
                parts.append(self.variant.size.name)
        return f"{' - '.join(parts)} (x{self.quantity})"

class Fulfillment(models.Model):
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="fulfillments")
    dealer = models.CharField(max_length=20)  # "Qikink" | "Printrove" | "Self"
    dealer_order_id = models.CharField(max_length=200, blank=True, null=True)  # id returned by dealer
    tracking_id = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=50, default="created")  # created, sent, confirmed, shipped, delivered
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    raw_response = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"Fulfillment {self.id} for Order {self.order.id} via {self.dealer}"

class DealerPayout(models.Model):
    dealer = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=200, blank=True, null=True)  # bank transfer id or invoice id
    status = models.CharField(
        max_length=20,
        choices=[("pending", "pending"), ("paid", "paid")],
        default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.dealer} - {self.amount} ({self.status})"

# ----------------------
# Marketing / Content
# ----------------------
class TeamMember(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    description = models.TextField()
    image = CloudinaryField("image")

    def __str__(self):
        return self.name


class Service(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    link = models.URLField()
    button_text = models.CharField(max_length=50)
    icon = models.CharField(max_length=50)

    def __str__(self):
        return self.title


class Client(models.Model):
    name = models.CharField(max_length=100)
    image = CloudinaryField("image")
    website = models.URLField(blank=True)

    def __str__(self):
        return self.name


# ----------------------
# Contact & Reviews
# ----------------------
class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()

    def __str__(self):
        return self.subject


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.IntegerField(default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.product.name}"
        return f"Anonymous - {self.product.name}"


# ----------------------
# Email OTP & Coupons
# ----------------------
class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)

    def __str__(self):
        return f"{self.user.email} - {self.otp}"


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    discount_percent = models.PositiveIntegerField(default=0)  # e.g. 10 for 10% off
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    users = models.ManyToManyField(User, related_name="coupons", blank=True)

    def __str__(self):
        return self.code

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_to

class Banner(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True, null=True)
    image = models.ImageField(upload_to='banners/')  # Cloudinary or local media
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['order']
