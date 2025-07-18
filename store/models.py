from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
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
        """Return the main image or fallback or a placeholder."""
        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image.image.url
        fallback_image = self.images.first()
        if fallback_image:
            return fallback_image.image.url
        return "/static/store/images/placeholder.png"  # Make sure this file exists

class Color(models.Model):
    name = models.CharField(max_length=30)
    hex_code = models.CharField(max_length=7)
    image = CloudinaryField('image', blank=True, null=True) 
    
    def __str__(self):
        return self.name

class Size(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.ForeignKey(Color, on_delete=models.CASCADE, null=True, blank=True)
    size = models.ForeignKey(Size, on_delete=models.CASCADE, null=True, blank=True)
    age_group = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.PositiveIntegerField(blank=True, null=True)
    image = CloudinaryField('image', blank=True, null=True)  # Variant-specific image

    def __str__(self):
        parts = [self.product.name]
        if self.color:
            parts.append(self.color.name)
        if self.size:
            parts.append(self.size.name)
        return " - ".join(parts)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image')
    is_main = models.BooleanField(default=False)  # Use this to flag the main image

    def __str__(self):
        return f"Image for {self.product.name}"

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_user_product_wishlist')
        ]

    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.product.name}"
        return f"Anonymous - {self.product.name}"

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_id = models.CharField(max_length=255)

    def __str__(self):
        return f"Order {self.id} - {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} (x{self.quantity})"

class TeamMember(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    description = models.TextField()
    image = CloudinaryField('image')
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
    image = CloudinaryField('image')
    website = models.URLField(blank=True)

    def __str__(self):
        return self.name

class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()

    def __str__(self):
        return self.subject

class Review(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.IntegerField(default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.product.name}"
        return f"Anonymous - {self.product.name}"
