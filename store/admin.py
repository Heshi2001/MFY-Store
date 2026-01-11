from django.contrib import admin
from .models import (
    Category, Product, ProductVariant, ProductImage, Color, ColorImage, Size, UserProfile, NewsletterSubscriber, Payment,
    Wishlist, Cart, CartItem, Order, OrderItem, AboutPage, SocialLink, Value, TeamMember, Service, Client,
    Contact, Review, Address, Fulfillment, Banner,HomeSection, PromoBanner,FAQ, Coupon, CouponUsage, SavedItem
)

from .qikink_api import send_order_to_qikink
from django.contrib import admin, messages
from django.utils.translation import ngettext
from mptt.admin import DraggableMPTTAdmin
from django.db.models import Avg, Count
from django.utils.html import format_html
from django.urls import reverse

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
        "name",
        "category",
        "dealer",
        "starting_price",        # ✅ derived from variants
        "total_stock",           # ✅ sum of variant stock
        "average_rating_display" # ✅ unchanged
    ]

    list_filter = [
        "category",
        "dealer",
        "has_size",
        "has_color",
        "has_capacity",
        "has_dimension",
    ]

    search_fields = ["name", "description", "sku"]

    inlines = [ProductVariantInline, ProductImageInline]

    readonly_fields = ["average_rating_readonly"]

    fieldsets = (
        ("Basic Info", {
            "fields": (
                "name",
                "category",
                "sku",
                "average_rating_readonly",
            )
        }),
        ("Attributes (controls UI)", {
            "fields": (
                "has_size",
                "has_color",
                "has_age_group",
                "has_dimension",
                "has_capacity",
                "has_weight",
                "has_pack_quantity",
                "has_shoe_size",
                "has_gender_fit",
            )
        }),
        ("Image Settings", {
            "fields": ("image_mode", "custom_image")
        }),
        ("Dealer Info", {
            "fields": ("dealer",)
        }),
        ("Description", {
            "fields": (
                "short_description",
                "special_offer_text",
                "description",
                "material",
            )
        }),
    )

    # ----------------- DERIVED VALUES -----------------

    def starting_price(self, obj):
        variant = obj.variants.order_by("price").first()
        if not variant:
            return "-"
        return variant.offer_price or variant.price
    starting_price.short_description = "Starting Price"

    def total_stock(self, obj):
        return obj.variants.aggregate(total=Count("stock"))["total"] or 0
    total_stock.short_description = "Stock"

    # ----------------- RATINGS (UNCHANGED) -----------------

    def average_rating_display(self, obj):
        stats = obj.reviews.aggregate(avg=Avg("rating"), total=Count("id"))
        avg = round(stats["avg"] or 0, 1)
        total = stats["total"] or 0

        if total > 0:
            review_url = (
                reverse("admin:store_review_changelist")
                + f"?product__id__exact={obj.id}"
            )
            return format_html(
                "⭐ {} <a href='{}'>({})</a>",
                avg,
                review_url,
                total,
            )
        return "⭐ 0.0 (0)"

    average_rating_display.short_description = "Rating (Reviews)"

    def average_rating_readonly(self, obj):
        stats = obj.reviews.aggregate(avg=Avg("rating"), total=Count("id"))
        avg = stats["avg"] or 0
        total = stats["total"] or 0
        return f"{round(avg, 1)} ★ based on {total} reviews"

    average_rating_readonly.short_description = "Average Rating"

@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    mptt_indent_field = "name"
    list_display = ("tree_actions", "indented_title", "slug", "parent")
    list_display_links = ("indented_title",)
    
# --- Variants & Images ---
@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "color",
        "size",
        "final_price",
        "stock",
    ]

    list_filter = ["product", "color", "size"]

    search_fields = ["product__name"]

    def final_price(self, obj):
        return obj.offer_price or obj.price
    final_price.short_description = "Price"

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image']
    search_fields = ['product__name']

class ColorImageInline(admin.TabularInline):
    model = ColorImage
    extra = 1

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'hex_code']
    search_fields = ['name']
    inlines = [ColorImageInline]

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

@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "saved_at")
    search_fields = ("user__username", "product__name")
    list_filter = ("saved_at",)
    
# --- Others ---

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone')
    search_fields = ('user__username', 'user__email', 'phone')

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
    list_display = [
        "id", "user", "subtotal", "shipping_cost", "tax_amount", "total_price", "coupon_display",
        "discount_percent", "payment_status", "status", "created_at"
    ]
    readonly_fields = ["created_at", "estimated_delivery"]
    search_fields = ["user__username", "payment_id", "razorpay_order_id", "razorpay_payment_id"]
    list_filter = ["status", "payment_status", "created_at"]
    inlines = [OrderItemInline, FulfillmentInline]
    actions = ["resend_to_qikink"]

    def coupon_display(self, obj):
        """Show coupon code if available."""
        return obj.coupon.code if obj.coupon else "-"
    coupon_display.short_description = "Coupon Code"

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

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "order_link",
        "method",
        "colored_status",
        "amount",
        "transaction_id",
        "created_at",
    )

    list_filter = ("method", "status", "created_at")
    search_fields = ("id", "user__email", "user__username", "order__id", "transaction_id")
    readonly_fields = ("created_at", "initiated_at", "updated_at", "gateway_response")

    ordering = ("-created_at",)

    # Show link to Order
    def order_link(self, obj):
        if obj.order:
            return format_html(f"<a href='/admin/store/order/{obj.order.id}/'>Order #{obj.order.id}</a>")
        return "-"
    order_link.short_description = "Order"

    # Colored status badge
    def colored_status(self, obj):
        color_map = {
            "PAID": "green",
            "PENDING": "orange",
            "FAILED": "red",
            "REFUNDED": "blue",
        }
        color = color_map.get(obj.status, "gray")
        return format_html(
            f"<span style='color:white; background:{color}; padding:3px 8px; border-radius:5px;'>{obj.status}</span>"
        )
    colored_status.short_description = "Status"

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

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order')
    ordering = ('order',)
    search_fields = ('question', 'answer')

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "discount_percent",
        "coupon_type",
        "is_active",
        "valid_from",
        "valid_to",
        "claimed_percent",
    )

    list_filter = (
        "is_active",
        "coupon_type",
        "valid_from",
        "valid_to",
    )

    search_fields = ("code", "description")
    ordering = ("-valid_from",)
    readonly_fields = ("is_valid_display",)

    fieldsets = (
        ("Basic Info", {
            "fields": (
                "code",
                "description",
                "image",
                "coupon_type",
                "is_active",
            )
        }),

        ("Discount Info", {
            "fields": (
                "discount_percent",
                "claimed_percent",
            )
        }),

        ("Validity Period", {
            "fields": (
                "valid_from",
                "valid_to",
            )
        }),

        ("Requirements", {
            "fields": (
                "min_spend",
                "buy_x",
                "get_y",
                "specific_user",
            )
        }),

        ("Status", {
            "fields": ("is_valid_display",)
        }),
    )

    def is_valid_display(self, obj):
        return obj.is_valid()

    is_valid_display.short_description = "Currently Valid?"
    is_valid_display.boolean = True

@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "coupon", "used_at")
    list_filter = ("used_at",)
    search_fields = ("user__username", "coupon__code")

@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    list_display = ("title", "subtitle", "mission", "vision")
    fieldsets = (
        (None, {
            "fields": ("title", "subtitle", "about_text", "background_image")
        }),
        ("Mission & Vision", {
            "fields": ("mission", "vision")
        }),
    )


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "icon_class")


@admin.register(Value)
class ValueAdmin(admin.ModelAdmin):
    list_display = ("title", "icon", "short_description")

    def short_description(self, obj):
        return obj.description[:60] + "..." if obj.description else ""
    short_description.short_description = "Description"


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "thumbnail", "social_count")

    filter_horizontal = ("social_links",)

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="border-radius:50%;">', obj.image.url)
        return "—"
    thumbnail.short_description = "Image"

    def social_count(self, obj):
        return obj.social_links.count()
    social_count.short_description = "Social Links"


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "icon", "button_text", "link")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "logo_preview")

    def logo_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" height="40">', obj.image.url)
        return "—"
    logo_preview.short_description = "Logo"

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "subscribed_at")
    search_fields = ("email",)
    ordering = ("-subscribed_at",)
