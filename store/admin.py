from django.contrib import admin
from .models import (
    Category, Product, ProductVariant, ProductImage, Color, Size,
    Wishlist, Cart, CartItem, Order, OrderItem, TeamMember,
    Service, Client, Contact, Review, Address, Fulfillment, Banner,HomeSection, PromoBanner
)

from .qikink_api import send_order_to_qikink
from django.contrib import admin, messages
from django.utils.translation import ngettext
from mptt.admin import DraggableMPTTAdmin

# --- Inlines ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ["total_price"]
    autocomplete_fields = ["product"]

# --- Product & Category ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'category',
        'price',
        'offer_price',
        'discount_percent',  # ✅ shows in list view
        'stock',
        'dealer',
        'rating',
    ]
    list_filter = ['category', 'dealer']
    search_fields = ['name', 'description', 'sku']
    inlines = [ProductVariantInline, ProductImageInline]
    readonly_fields = ['discount_percent']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'category', 'sku', 'price', 'offer_price', 'discount_percent', 'stock', 'rating')
        }),
        ('Image Settings', {
            'fields': ('image_mode', 'custom_image')
        }),
        ('Dealer Info', {
            'fields': ('dealer',)
        }),
        ('Description', {
            'fields': ('description', 'material')
        }),
    )
        
@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    mptt_indent_field = "name"
    list_display = ("tree_actions", "indented_title", "slug", "parent")
    list_display_links = ("indented_title",)
    
# --- Variants & Images ---
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

# --- Wishlist ---
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product']
    search_fields = ['user__username', 'product__name']

# --- Cart ---
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    search_fields = ['user__username']
    inlines = [CartItemInline]

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'total_price']
    search_fields = ['cart__user__username', 'product__name']
    list_editable = ['quantity']

# --- Others ---
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

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'active', 'order')
    list_editable = ('active', 'order')
    fields = ('title', 'subtitle', 'image', 'mobile_image', 'order', 'active')

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "first_name", "last_name", "city", "is_default", "address_type")


# --- Orders ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price']
    autocomplete_fields = ['product']

class FulfillmentInline(admin.TabularInline):
    model = Fulfillment
    extra = 0
    readonly_fields = ['dealer', 'status', 'raw_response', 'created_at']  # 🟢 fixed

@admin.register(Fulfillment)
class FulfillmentAdmin(admin.ModelAdmin):   # ✅ proper ModelAdmin
    list_display = ("order", "dealer", "status", "created_at")
    list_filter = ("dealer", "status")
    search_fields = ("order__id", "dealer")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_price', 'status', 'created_at', 'payment_id']
    readonly_fields = ['created_at']
    search_fields = ['user__username', 'payment_id']
    list_filter = ['status', 'created_at']
    inlines = [OrderItemInline, FulfillmentInline]
    actions = ["resend_to_qikink"]

    def resend_to_qikink(self, request, queryset):
        success, failed = 0, 0
        for order in queryset:
            try:
                result = send_order_to_qikink(order)
                Fulfillment.objects.create(
                    order=order,
                    dealer="Qikink", 
                    status="success" if result.get("status") == "success" else "failed",
                    raw_response=result,
                )
                success += 1
            except Exception as e:
                Fulfillment.objects.create(
                    order=order,
                    dealer="Qikink",
                    status="failed",
                    raw_response={"error": str(e)},
                )
                failed += 1

        self.message_user(
            request,
            ngettext(
                "%d order was resent successfully. %d failed.",
                "%d orders were resent successfully. %d failed.",
                success,
            ) % (success, failed),
            messages.SUCCESS if failed == 0 else messages.WARNING,
        )
    
    resend_to_qikink.short_description = "Resend selected orders to Qikink"

@admin.register(HomeSection)
class HomeSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "product_limit", "order", "active")
    list_editable = ("order", "active")

@admin.register(PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    list_display = ("short_message", "is_active", "start_date", "end_date", "created_at")
    list_editable = ("is_active",)
    search_fields = ("message",)
    list_filter = ("is_active",)

    def short_message(self, obj):
        return obj.message[:60]
    short_message.short_description = "Banner Message"
