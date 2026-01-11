from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField
from django.utils import timezone
from datetime import timedelta, date
from mptt.models import MPTTModel, TreeForeignKey
from django.utils.text import slugify
from django.conf import settings 
from django.urls import reverse
from decimal import Decimal

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

class HomeSection(models.Model):
    title = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="If set, products will be pulled from this category."
    )
    product_limit = models.PositiveIntegerField(default=8)
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title

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

    category = models.ForeignKey(
        "Category", on_delete=models.CASCADE, related_name="products"
    )
    sku = models.CharField(max_length=100, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)

    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=200, blank=True, null=True)
    special_offer_text = models.CharField(max_length=150, blank=True, null=True)
    material = models.CharField(max_length=100, blank=True, null=True)

    dealer = models.CharField(
        max_length=20, choices=DEALER_CHOICES, default="Self"
    )

    # 🖼️ Image mode
    image_mode = models.CharField(
        max_length=20, choices=IMAGE_MODE_CHOICES, default="qikink"
    )
    custom_image = CloudinaryField("custom_image", blank=True, null=True)

    # 🚦 ATTRIBUTE FLAGS (THIS CONTROLS UI + VALIDATION)
    has_size = models.BooleanField(default=False)
    has_color = models.BooleanField(default=False)
    has_age_group = models.BooleanField(default=False)

    has_dimension = models.BooleanField(default=False)
    has_capacity = models.BooleanField(default=False)
    has_weight = models.BooleanField(default=False)
    has_pack_quantity = models.BooleanField(default=False)
    has_shoe_size = models.BooleanField(default=False)
    has_gender_fit = models.BooleanField(default=False)

    # 🚚 Optional logistics
    shipping_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    # ================== LOGIC ==================

    def get_vendor_defaults(self):
        defaults = {
            "Qikink": {"shipping": Decimal("49.00"), "tax": Decimal("18.00")},
            "Printrove": {"shipping": Decimal("59.00"), "tax": Decimal("12.00")},
            "Self": {"shipping": Decimal("40.00"), "tax": Decimal("10.00")},
        }
        return defaults.get(self.dealer, defaults["Self"])

    def get_shipping_cost(self):
        return (
            self.shipping_price
            if self.shipping_price is not None
            else self.get_vendor_defaults()["shipping"]
        )

    def get_tax_rate(self):
        return (
            self.tax_rate
            if self.tax_rate is not None
            else self.get_vendor_defaults()["tax"]
        )

    # ---------------- DISPLAY HELPERS ----------------

    def get_base_variant(self):
        """Cheapest variant (used for listing price)"""
        return self.variants.order_by("price").first()

    def get_display_price(self):
        variant = self.get_base_variant()
        if not variant:
            return None
        return variant.offer_price or variant.price

    @property
    def in_stock(self):
        """Product is in stock if ANY variant has stock"""
        return self.variants.filter(stock__gt=0).exists()

    def get_main_image_url(self):
        if self.image_mode == "custom" and self.custom_image:
            return self.custom_image.url

        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image.image.url

        fallback_image = self.images.first()
        if fallback_image:
            return fallback_image.image.url

        return "/static/store/images/placeholder.png"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("product_detail", args=[self.id])

    def __str__(self):
        return self.name

# ---------- Color & Size ----------

class Color(models.Model):
    name = models.CharField(max_length=30)
    hex_code = models.CharField(max_length=7)
    image = CloudinaryField("image", blank=True, null=True)

    def __str__(self):
        return self.name

class ColorImage(models.Model):
    color = models.ForeignKey(
        Color,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = CloudinaryField("image")
    is_main = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.color.name} image"

class Size(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]

class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )

    # Apparel / Core
    color = models.ForeignKey(
        "Color", on_delete=models.CASCADE, null=True, blank=True
    )
    size = models.ForeignKey(
        "Size", on_delete=models.CASCADE, null=True, blank=True
    )
    age_group = models.CharField(max_length=20, null=True, blank=True)

    # Universal attributes
    dimension = models.CharField(max_length=30, null=True, blank=True)   # "40x60 cm"
    capacity = models.CharField(max_length=20, null=True, blank=True)    # "500 ml"
    weight = models.CharField(max_length=20, null=True, blank=True)      # "1 kg"
    pack_quantity = models.PositiveIntegerField(null=True, blank=True)
    shoe_size = models.CharField(max_length=10, null=True, blank=True)
    gender_fit = models.CharField(max_length=10, null=True, blank=True)

    # Pricing & stock
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, editable=False
    )
    stock = models.PositiveIntegerField(default=0)

    # Variant image override
    image = CloudinaryField("image", blank=True, null=True)

    # ================== LOGIC ==================

    def save(self, *args, **kwargs):
        if self.offer_price and self.offer_price < self.price:
            self.discount_percent = (
                (self.price - self.offer_price) / self.price * Decimal("100")
            ).quantize(Decimal("0.01"))
        else:
            self.discount_percent = Decimal("0.00")
        super().save(*args, **kwargs)

    @property
    def final_price(self):
        return self.offer_price or self.price

    @property
    def in_stock(self):
        return self.stock > 0

    def __str__(self):
        parts = [self.product.name]
        if self.color:
            parts.append(self.color.name)
        if self.size:
            parts.append(self.size.name)
        if self.age_group:
            parts.append(self.age_group)
        if self.shoe_size:
            parts.append(f"Shoe {self.shoe_size}")
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

    @property
    def avatar_url(self):
        if self.profile_image:
            return self.profile_image.url
        return '/static/store/images/avatar-placeholder.png'

class Address(models.Model):
    ADDRESS_TYPES = (
        ("shipping", "Shipping"),
        ("billing", "Billing"),
        ("home", "Home"),
        ("office", "Office"),
        ("other", "Other"),
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
    alert_enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_user_product_wishlist")
        ]

    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.product.name}"
        return f"Anonymous - {self.product.name}"

class StockNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey("Product", on_delete=models.CASCADE)
    is_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notify {self.user} when {self.product.name} restocks"

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
                            product=item.product,
                            variant=item.variant,  # ✅ REQUIRED
                        )
                        if not created:
                            cart_item.quantity += item.quantity
                        else:
                            cart_item.quantity = item.quantity

                        cart_item.save()

                    guest_cart.delete()

        elif session_key:
            cart = self.filter(session_key=session_key).first()
            if not cart:
                cart = self.create(session_key=session_key)
        else:
            raise ValueError("Either user or session_key must be provided.")
        
        items = cart.items.select_related("product", "variant").all()
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
        """
        Pricing comes ONLY from ProductVariant.
        Product has NO price field.
        """
        if not self.variant:
            return 0  # safety guard (should never happen)

        price = self.variant.offer_price or self.variant.price
        return price * self.quantity

class SavedItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True )
    
    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} saved {self.product.name}"

# ----------------------
# Marketing / Content
# ----------------------

class AboutPage(models.Model):
    """Main About Page settings"""
    title = models.CharField(max_length=100, default="About Us")
    subtitle = models.CharField(max_length=150, blank=True, null=True)
    about_text = models.TextField(blank=True, null=True)
    mission = models.TextField(blank=True, null=True, help_text="Mission statement text")
    vision = models.TextField(blank=True, null=True, help_text="Vision statement text")
    background_image = CloudinaryField('image', blank=True, null=True)

    class Meta:
        verbose_name = "About Page"
        verbose_name_plural = "About Page"

    def __str__(self):
        return self.title


class SocialLink(models.Model):
    """Social media link for AboutPage or TeamMember"""
    name = models.CharField(max_length=50)
    url = models.URLField()
    icon_class = models.CharField(
        max_length=50,
        help_text='Font Awesome class name (e.g. "fa-facebook", "fa-twitter")'
    )

    def __str__(self):
        return self.name


class Value(models.Model):
    """Core values shown on About page"""
    icon = models.CharField(
        max_length=50,
        help_text='Font Awesome icon (e.g. "fa-heart")'
    )
    title = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.title


class TeamMember(models.Model):
    """Team member profiles"""
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = CloudinaryField('image', blank=True, null=True)
    social_links = models.ManyToManyField(SocialLink, blank=True, related_name="team_members")

    def __str__(self):
        return self.name


class Service(models.Model):
    """Services displayed on About page"""
    icon = models.CharField(
        max_length=50,
        help_text='Font Awesome icon (e.g. "fa-truck", "fa-star")'
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    link = models.CharField(
        max_length=200,
        blank=True,
        help_text="Use relative URLs like /shipping/ or /contact/"
    )
    button_text = models.CharField(max_length=50, blank=True, null=True, default="Learn More")

    def __str__(self):
        return self.title


class Client(models.Model):
    """Logos of partner brands or clients"""
    name = models.CharField(max_length=100)
    image = CloudinaryField('image', blank=True, null=True)

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
    COUPON_TYPES = [
        ("GENERIC", "Generic (anyone can use)"),
        ("FIRST_ORDER", "First Order Only"),
        ("MIN_SPEND", "Minimum Spend Required"),
        ("BUY_X_GET_Y", "Buy X Get Y"),
        ("USER_SPECIFIC", "Specific User Only"),
    ]

    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    # Image field (Cloudinary)
    image = CloudinaryField("coupon_image", blank=True, null=True)

    claimed_percent = models.PositiveIntegerField(default=0)
    discount_percent = models.PositiveIntegerField(default=0)

    valid_from = models.DateTimeField(blank=True, null=True)
    valid_to = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPES, default="GENERIC")
    min_spend = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    buy_x = models.PositiveIntegerField(null=True, blank=True)
    get_y = models.PositiveIntegerField(null=True, blank=True)
    specific_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def time_left(self):
        if not self.valid_to:
            return (0, 0, 0)
        delta = self.valid_to - timezone.now()
        if delta.total_seconds() <= 0:
            return (0, 0, 0)
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        seconds = delta.seconds % 60
        return (hours, minutes, seconds)

    def is_valid(self, user=None, total=None):
        now = timezone.now()

        if not self.is_active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False

        if self.coupon_type == "FIRST_ORDER":
            from store.models import Order
            if Order.objects.filter(user=user).exists():
                return False

        if self.coupon_type == "MIN_SPEND" and total is not None:
            if total < (self.min_spend or 0):
                return False

        if self.coupon_type == "USER_SPECIFIC" and self.specific_user != user:
            return False

        return True

    def __str__(self):
        return f"{self.code} ({self.discount_percent}% off)"

class CouponUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="coupon_usages")
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="usages")
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "coupon")

    def __str__(self):
        return f"{self.user.username} used {self.coupon.code} at {self.used_at}"

# ----------------------
# Orders
# ----------------------

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    
    # 🟢 Child Totals (stored for invoice & calculations)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ✅ Totals & Discounts
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # ✅ Razorpay fields
    payment_id = models.CharField(max_length=255, blank=True, null=True)
    order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)

    # ✅ Payment / Status
    payment_status = models.CharField(max_length=20, default="PENDING")
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Processing", "Processing"),
        ("Shipped", "Shipped"),
        ("Out for Delivery", "Out for Delivery"),
        ("Delivered", "Delivered"),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Pending")

    # ✅ Addresses
    shipping_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True, related_name="shipping_orders"
    )
    billing_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_orders"
    )
    
    # 🟢 Address Snapshot (saved permanently)
    shipping_first_name = models.CharField(max_length=50, blank=True, null=True)
    shipping_last_name = models.CharField(max_length=50, blank=True, null=True)
    shipping_phone = models.CharField(max_length=15, blank=True, null=True)
    shipping_address_line1 = models.CharField(max_length=255, blank=True, null=True)
    shipping_address_line2 = models.CharField(max_length=255, blank=True, null=True)
    shipping_city = models.CharField(max_length=100, blank=True, null=True)
    shipping_state = models.CharField(max_length=100, blank=True, null=True)
    shipping_country = models.CharField(max_length=100, blank=True, null=True)
    shipping_postal_code = models.CharField(max_length=30, blank=True, null=True)

    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)

    # ✅ Estimated Delivery
    estimated_delivery = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.estimated_delivery:
            self.estimated_delivery = date.today() + timedelta(days=5)
        super().save(*args, **kwargs)

    @property
    def delivery_progress(self):
        """
        Return a percentage for UI progress bar.
        """
        progress_map = {
            "Pending": 20,
            "Processing": 40,
            "Shipped": 60,
            "Out for Delivery": 80,
            "Delivered": 100,
        }
        return progress_map.get(self.status, 0)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

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

class Payment(models.Model):
    PAYMENT_METHODS = [
        ("COD", "Cash on Delivery"),
        ("RAZORPAY", "Razorpay"),
        ("STRIPE", "Stripe"),
        ("WALLET", "Wallet"),
    ]

    PAYMENT_STATUS = [
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="payments"
    )

    order = models.OneToOneField(
        Order, on_delete=models.CASCADE,
        related_name="payment"
    )

    method = models.CharField(
        max_length=20, choices=PAYMENT_METHODS,
        default="RAZORPAY"
    )

    status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS,
        default="PENDING"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Razorpay/Stripe transaction IDs
    transaction_id = models.CharField(max_length=200, blank=True, null=True)
    gateway_response = models.JSONField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    initiated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Refund
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_id = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"Payment #{self.id} - {self.status} - {self.user}"

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
# Banner @ FAQ
# ----------------------

class Banner(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True, null=True)
    image = models.ImageField(upload_to='banners/')  # Main desktop image
    mobile_image = models.ImageField(upload_to='banners/mobile/', blank=True, null=True)  # Optional mobile version
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['order']

class PromoBanner(models.Model):
    message = models.TextField(
        help_text="Write promo text with emojis and HTML (e.g. 🔥 Get 10% OFF! <a href='/shop'>Shop Now</a>)"
    )
    is_active = models.BooleanField(default=True, help_text="Enable or disable this banner manually.")
    start_date = models.DateTimeField(blank=True, null=True, help_text="Optional: Show banner starting from this date.")
    end_date = models.DateTimeField(blank=True, null=True, help_text="Optional: Hide banner after this date.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.message[:60]

    @property
    def is_currently_active(self):
        """Check if banner is within active date range."""
        now = timezone.now()
        if self.start_date and self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return self.is_active

class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0, help_text="Order for display priority")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.question

class ReturnRequest(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
