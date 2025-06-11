from django.contrib import admin
from .models import (
    Category, Product, ProductVariant, ProductImage, Color, Size,
    Wishlist, Cart, Order, OrderItem, TeamMember, Service, Client, Contact, Review
)

# Inline for adding images directly when editing a product
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

# Inline for adding variants directly when editing a product
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'offer_price', 'stock']
    list_filter = ['category']
    search_fields = ['name', 'description']
    inlines = [ProductVariantInline, ProductImageInline]

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'color', 'size', 'quantity']
    list_filter = ['color', 'size']
    search_fields = ['product__name']

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image']
    search_fields = ['product__name']

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'hex_code', 'image']
    search_fields = ['name']

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product']
    search_fields = ['user__username', 'product__name']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'quantity']
    search_fields = ['user__username', 'product__name']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_price', 'created_at', 'payment_id']
    readonly_fields = ['created_at']
    search_fields = ['user__username', 'payment_id']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price']

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'role']
    search_fields = ['name']

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['title', 'button_text']

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'website']
    search_fields = ['name']

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject']
    search_fields = ['name', 'email']
    readonly_fields = ['name', 'email', 'subject', 'message']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['product__name', 'user__username']
