from django.contrib import admin
from .models import (
    # Product
    Category, Product, ProductVariant, ProductImage, Color, ColorImage, Size,

    # User / Marketing
    UserProfile, NewsletterSubscriber, SearchQuery,

    # Cart / Orders
    Cart, CartItem, Wishlist,
    Order, OrderItem, ReturnRequest, Payment,

    # CMS
    AboutPage, SocialLink, Value, TeamMember, Service, Client,
    Banner, HomeSection, PromoBanner, FAQ,

    # Others
    Brand, StockLog, Customization,
    Coupon, CouponUsage,
    SavedItem,
    ProductRelation,
    ProductAccordion, AccordionTemplate,
    Contact, Review, Address, Fulfillment,
)

from .qikink_api import send_order_to_qikink
from django.contrib import admin, messages
from django.utils.translation import ngettext
from mptt.admin import DraggableMPTTAdmin
from django.db.models import Avg, Count, Sum
from django.utils.html import format_html
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils import timezone

@admin.register(Brand)
class BrandAdmin(DraggableMPTTAdmin):

    mptt_indent_field = "name"

    list_display = (
        "tree_actions",
        "indented_title",
        "slug",
        "parent",
        "is_active",
    )

    list_display_links = ("indented_title",)

    search_fields = (
        "name",
        "slug",
    )

    list_filter = (
        "is_active",
    )

    prepopulated_fields = {
        "slug": ("name",)
    }
    
# --- Inlines ---
class ProductImageInline(admin.TabularInline):

    model = ProductImage
    extra = 1

    fields = (
        "image",
        "is_main",
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = (
        "sku",
        "color",
        "size",
        "age_group",
        "dimension",
        "capacity",
        "weight",
        "pack_quantity",
        "shoe_size",
        "gender_fit",
        "price",
        "offer_price",
        "discount_percent",  # ← readonly, auto-calculated
        "stock",
        "is_active",
        "image",
        "created_at",
    )
    readonly_fields = (
        "discount_percent",
        "created_at",
    )

    # ✅ Show validation errors inline in admin
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['price'].required = True
        return formset

class ProductAccordionInline(admin.TabularInline):

    model = ProductAccordion

    extra = 1

    fields = (
        "title",
        "order",
        "is_active",
        "content",
        "open_count",
    )

    readonly_fields = (
        "open_count",
    )
    
    sortable_field_name = "order"

    ordering = ("order",)

class CartItemInline(admin.TabularInline):

    model = CartItem

    extra = 0

    readonly_fields = (
        "total_price",
    )

    autocomplete_fields = (
        "product",
    )

class ColorImageInline(admin.TabularInline):

    model = ColorImage

    extra = 1

    fields = (
        "image",
        "is_main",
    )

class ProductRelationInline(admin.TabularInline):

    model = ProductRelation
    fk_name = "product"
    extra = 1

# --- Product & Category ---

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "brand",
        "category",
        "product_type",
        "dealer",
        "is_active",
        "track_inventory",
        "starting_price",
        "total_stock_display",
        "average_rating_display",
        "created_at",
    )

    list_filter = (
        "brand",
        "product_type",
        "category",
        "dealer",
        "is_active",
        "track_inventory",

        "has_size",
        "has_color",
        "has_capacity",
        "has_dimension",
    )

    search_fields = (
        "name",
        "sku",
        "brand__name",
        "description",
        "keywords",
    )

    prepopulated_fields = {
        "slug": ("name",)
    }

    autocomplete_fields = (
        "brand",
        "category",
    )

    readonly_fields = (
        "average_rating_readonly",
        "created_at",
        "updated_at",
    )

    inlines = (
        ProductVariantInline,
        ProductImageInline,
        ProductAccordionInline,
        ProductRelationInline, 
    )

    fieldsets = (

        ("Brand & Type", {
            "fields": (
                "brand",
                "product_type",
                "is_active",
                "track_inventory",
            )
        }),

        ("Basic Info", {
            "fields": (
                "name",
                "slug",
                "category",
                "sku",
                "average_rating_readonly",
            )
        }),

        ("Attributes (Controls Variant UI)", {
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

        ("Images", {
            "fields": (
                "image_mode",
                "custom_image",
            )
        }),

        ("Dealer / Fulfillment", {
            "fields": (
                "dealer",
                "shipping_price",
                "tax_rate",
            )
        }),

        ("Descriptions", {
            "fields": (
                "short_description",
                "special_offer_text",
                "keywords",
                "description",
            )
        }),

        ("Timestamps", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    # =====================================================
    # SECURITY: HTML SANITIZATION
    # =====================================================

    def save_model(self, request, obj, form, change):

        super().save_model(request, obj, form, change)

        for acc in obj.accordions.all():
            acc.content = strip_tags(acc.content)
            acc.save(update_fields=["content"])

    # =====================================================
    # PRICE DISPLAY
    # =====================================================

    def starting_price(self, obj):

        variant = obj.get_base_variant()

        if not variant:
            return "-"

        return variant.final_price

    starting_price.short_description = "Starting Price"


    # =====================================================
    # STOCK DISPLAY (FIXED)
    # =====================================================

    def total_stock_display(self, obj):

        if not obj.track_inventory:
            return "Not tracked"

        total = obj.variants.aggregate(
            total=Sum("stock")
        )["total"]

        return total or 0

    total_stock_display.short_description = "Total Stock"


    # =====================================================
    # RATINGS
    # =====================================================

    def average_rating_display(self, obj):

        stats = obj.reviews.aggregate(
            avg=Avg("rating"),
            total=Count("id")
        )

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

    average_rating_display.short_description = "Rating"


    def average_rating_readonly(self, obj):

        stats = obj.reviews.aggregate(
            avg=Avg("rating"),
            total=Count("id")
        )

        avg = stats["avg"] or 0
        total = stats["total"] or 0

        return f"{round(avg, 1)} ★ based on {total} reviews"

    average_rating_readonly.short_description = "Average Rating"



# ============================================================
# CATEGORY ADMIN
# ============================================================

@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):

    mptt_indent_field = "name"

    list_display = (
        "tree_actions",
        "indented_title",
        "slug",
        "parent",
    )

    list_display_links = (
        "indented_title",
    )

    search_fields = (
        "name",
        "slug",
    )
    actions = ['rebuild_tree']

    def rebuild_tree(self, request, queryset):
        Category.objects.rebuild()
        self.message_user(request, "✅ Category tree rebuilt successfully.")
    rebuild_tree.short_description = "Rebuild MPTT tree"

# ============================================================
# VARIANT ADMIN
# ============================================================

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "sku",
        "color",
        "size",
        "price",
        "offer_price",
        "discount_percent",
        "final_price_display",  # ← new column
        "stock",
        "is_active",
        "created_at",
    )
    list_filter = (
        "is_active",
        "color",
        "size",
    )
    search_fields = (
        "product__name",
        "sku",
    )
    autocomplete_fields = ("product",)

    # ✅ Show what customer pays in list view
    def final_price_display(self, obj):
        return f"₹{obj.final_price}"
    final_price_display.short_description = "Customer Pays"

    # ✅ Highlight zero/invalid prices in red
    def price(self, obj):
        from django.utils.html import format_html
        if not obj.price or obj.price <= 0:
            return format_html(
                '<span style="color:red;font-weight:bold">₹{} ⚠️</span>',
                obj.price
            )
        return f"₹{obj.price}"
        
# ============================================================
# PRODUCT IMAGE ADMIN
# ============================================================

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "is_main",
        "created_at",
    )

    search_fields = (
        "product__name",
    )


# ============================================================
# COLOR ADMIN
# ============================================================

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "hex_code",
    )

    search_fields = (
        "name",
    )

    inlines = (
        ColorImageInline,
    )


# ============================================================
# SIZE ADMIN
# ============================================================

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):

    list_display = (
        "name",
    )

    search_fields = (
        "name",
    )


# ============================================================
# STOCK LOG ADMIN
# ============================================================

@admin.register(StockLog)
class StockLogAdmin(admin.ModelAdmin):

    list_display = (
        "variant",
        "change",
        "reason",
        "created_by",
        "created_at",
    )

    list_filter = (
        "reason",
        "created_at",
    )

    search_fields = (
        "variant__product__name",
        "variant__sku",
    )

    autocomplete_fields = (
        "variant",
        "created_by",
    )


# ============================================================
# CUSTOMIZATION ADMIN
# ============================================================

@admin.register(Customization)
class CustomizationAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "created_at",
    )

    search_fields = (
        "product__name",
    )


# ============================================================
# ACCORDION TEMPLATE ADMIN
# ============================================================

@admin.register(AccordionTemplate)
class AccordionTemplateAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "schema_key",
        "is_active",
    )

    list_editable = (
        "is_active",
    )

    readonly_fields = (
        "schema_key",
    )

    search_fields = (
        "title",
        "schema_key",
    )

    fieldsets = (

        ("Template Info", {
            "fields": (
                "title",
                "schema_key",
                "is_active",
            )
        }),

        ("Content", {
            "fields": (
                "default_content",   # ✅ FIXED
            )
        }),
    )

    def save_model(self, request, obj, form, change):

        obj.default_content = strip_tags(obj.default_content)  # ✅ FIXED

        super().save_model(request, obj, form, change)

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
class FulfillmentAdmin(admin.ModelAdmin):

    list_display  = [
        "id", "order", "dealer", "status",
        "tracking_id", "courier_name", "aftership_registered", "updated_at"
    ]
    list_filter   = ["dealer", "status", "aftership_registered"]
    search_fields = ["order__id", "tracking_id", "dealer_order_id"]
    readonly_fields = ["aftership_registered", "created_at", "updated_at", "raw_response"]

    # Fields you can edit manually
    fields = [
        "order", "dealer", "dealer_order_id",
        "status", "tracking_id", "courier_name",
        "aftership_registered", "raw_response",
        "created_at", "updated_at",
    ]

    def save_model(self, request, obj, form, change):
        """
        When you save a Fulfillment with a tracking_id for the first time,
        auto-register with AfterShip immediately.
        """
        is_new_awb = (
            obj.tracking_id
            and not obj.aftership_registered
        )

        super().save_model(request, obj, form, change)

        if is_new_awb:
            from store.services.aftership_service import register_tracking
            result = register_tracking(
                awb_number   = obj.tracking_id,
                order_id     = obj.order.id,
                courier_slug = None,  # auto-detect
            )

            if result.get("data"):
                obj.aftership_registered = True
                obj.save(update_fields=["aftership_registered"])

                # Also update order status to Shipped
                order = obj.order
                if order.status in ["Pending", "Processing"]:
                    order.status = "Shipped"
                    order.save(update_fields=["status"])

                self.message_user(
                    request,
                    f"✅ AWB {obj.tracking_id} registered with AfterShip. Order #{order.id} marked as Shipped.",
                    level="success"
                )
            else:
                self.message_user(
                    request,
                    f"⚠️ AWB saved but AfterShip registration failed. Check your API key.",
                    level="warning"
                )
# ════════════════════════════════════════
# Order Admin
# ════════════════════════════════════════
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = [
        "id",
        "user",
        "total_price",
        "payment_status",
        "status",
        "delivery_progress_bar",   # 🔥 visual progress
        "created_at",
        "delivered_at",
        "cancelled_at",
    ]

    readonly_fields = [
        "created_at",
        "estimated_delivery",
        "delivered_at",
        "cancelled_at",
        "returned_at",
    ]

    search_fields = [
        "user__username",
        "payment_id",
        "razorpay_order_id",
        "razorpay_payment_id"
    ]

    list_filter = [
        "status",
        "payment_status",
        "created_at",
        "delivered_at",
    ]

    inlines = [OrderItemInline]
    actions = ["resend_to_qikink"]

    fieldsets = (
        ("Order Info", {
            "fields": ("user", "status", "payment_status")
        }),
        ("Amounts", {
            "fields": (
                "subtotal",
                "shipping_cost",
                "tax_amount",
                "total_price",
                "discount_percent",
            )
        }),
        ("Lifecycle", {
            "fields": (
                "created_at",
                "delivered_at",
                "cancelled_at",
                "returned_at",
            )
        }),
    )

    # ════════════════════════════════
    # Progress Bar
    # ════════════════════════════════
    def delivery_progress_bar(self, obj):
        progress = obj.delivery_progress
        return format_html(
            '<div style="width:110px;background:#222;border-radius:6px;">'
            '<div style="width:{}%;background:#22c55e;color:white;'
            'text-align:center;border-radius:6px;font-size:12px;">{}%</div>'
            '</div>',
            progress,
            progress
        )
    delivery_progress_bar.short_description = "Progress"

    # ════════════════════════════════
    # Auto Timestamp Logic
    # ════════════════════════════════
    def save_model(self, request, obj, form, change):
        if change:
            old_obj = Order.objects.get(pk=obj.pk)

            if obj.status == "Delivered" and not old_obj.delivered_at:
                obj.delivered_at = timezone.now()

            elif obj.status == "Cancelled" and not old_obj.cancelled_at:
                obj.cancelled_at = timezone.now()

            elif obj.status == "Returned" and not old_obj.returned_at:
                obj.returned_at = timezone.now()

        super().save_model(request, obj, form, change)

    # ════════════════════════════════
    # Coupon Display
    # ════════════════════════════════
    def coupon_display(self, obj):
        return obj.coupon.code if obj.coupon else "-"
    coupon_display.short_description = "Coupon Code"

    # ════════════════════════════════
    # Qikink Action
    # ════════════════════════════════
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


# ════════════════════════════════════════
# Return Request Admin
# ════════════════════════════════════════
@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):

    list_display = [
        "id",
        "order",
        "user",
        "status",
        "created_at",
        "approved_at",
        "completed_at",
    ]

    list_filter = ["status", "created_at"]

    search_fields = ["order__id", "user__username"]

    readonly_fields = [
        "created_at",
        "approved_at",
        "picked_at",
        "completed_at",
        "rejected_at",
    ]

    # 🔥 YOUR LOGIC (cleaned + fixed)
    def save_model(self, request, obj, form, change):

        if change:
            old = ReturnRequest.objects.get(pk=obj.pk)

            if obj.status == "Approved" and not old.approved_at:
                obj.approved_at = timezone.now()

            elif obj.status == "Picked" and not old.picked_at:
                obj.picked_at = timezone.now()

            elif obj.status == "Completed" and not old.completed_at:
                obj.completed_at = timezone.now()

            elif obj.status == "Rejected" and not old.rejected_at:
                obj.rejected_at = timezone.now()

        super().save_model(request, obj, form, change)

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

# ============================================================
# SEARCH QUERY ADMIN (Trending Searches)
# ============================================================

@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):

    list_display = (
        "query",
        "count",
        "last_searched",
    )

    search_fields = (
        "query",
    )

    ordering = (
        "-count",
    )

    readonly_fields = (
        "count",
        "last_searched",
    )

# ============================================================
# RELATED PRODUCTS ADMIN
# ============================================================

@admin.register(ProductRelation)
class ProductRelationAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "related_product",
    )

    autocomplete_fields = (
        "product",
        "related_product",
    )

    search_fields = (
        "product__name",
        "related_product__name",
    )

