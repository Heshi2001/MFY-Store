from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField
from django.utils import timezone
from datetime import timedelta

# ----------------------
# Category & Product
# ----------------------
class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    material = models.CharField(max_length=100, blank=True, null=True)
    rating = models.IntegerField(default=5)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    def get_main_image_url(self):
        """Return the main image or fallback image or placeholder."""
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
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_cart_product")
        ]

    def __str__(self):
        return f"{self.product.name} (x{self.quantity})"

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

    def __str__(self):
        return f"Order {self.id} - {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} (x{self.quantity})"


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
