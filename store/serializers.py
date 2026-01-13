from rest_framework import serializers
from .models import Product, ProductImage, ProductVariant, Category

# ✅ Fallback placeholder image
PLACEHOLDER_IMAGE = "/static/store/images/placeholder.png"


def normalize_image_url(url: str, size: int = None) -> str:
    """
    Cleans up image URLs:
    - Strips invalid 'image/upload/https://' prefixes
    - Applies Cloudinary transformations if needed
    - Falls back to placeholder if missing
    """
    if not url:
        return PLACEHOLDER_IMAGE

    # 1. Fix bad prefix
    if url.startswith("image/upload/https://"):
        url = url.replace("image/upload/", "", 1)

    # 2. Apply Cloudinary transform
    if "res.cloudinary.com" in url and size:
        return url.replace("/upload/", f"/upload/w_{size},f_auto,q_auto/")

    return url


class ProductImageSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    full_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["image", "is_main", "thumbnail_url", "full_url"]

    def get_thumbnail_url(self, obj):
        # ✅ Updated to handle string URLs from Qikink or ImageField
        url = obj.image if isinstance(obj.image, str) else getattr(obj.image, "url", None)
        return normalize_image_url(url, size=400)

    def get_full_url(self, obj):
        url = obj.image if isinstance(obj.image, str) else getattr(obj.image, "url", None)
        return normalize_image_url(url, size=800)


class ProductVariantSerializer(serializers.ModelSerializer):
    color = serializers.StringRelatedField()
    size = serializers.StringRelatedField()
    thumbnail_url = serializers.SerializerMethodField()
    full_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id", "color", "size", "age_group", "stock" , "image",
            "thumbnail_url", "full_url"
        ]

    def get_thumbnail_url(self, obj):
        url = obj.image if isinstance(obj.image, str) else getattr(obj.image, "url", None)
        return normalize_image_url(url, size=400)

    def get_full_url(self, obj):
        url = obj.image if isinstance(obj.image, str) else getattr(obj.image, "url", None)
        return normalize_image_url(url, size=800)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]

class ProductSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    variants = ProductVariantSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)

    display_price = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()

    main_thumbnail_url = serializers.SerializerMethodField()
    main_full_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "dealer",
            "description",
            "category",
            "images",
            "variants",
            "display_price",
            "in_stock",
            "main_thumbnail_url",
            "main_full_url",
        ]

    def get_display_price(self, obj):
        variant = obj.get_base_variant()
        if not variant:
            return None
        return variant.offer_price or variant.price

    def get_in_stock(self, obj):
        return obj.variants.filter(stock__gt=0).exists()

    def get_main_thumbnail_url(self, obj):
        url = obj.get_main_image_url()
        return normalize_image_url(url, size=400)

    def get_main_full_url(self, obj):
        url = obj.get_main_image_url()
        return normalize_image_url(url, size=800)

    def get_images(self, obj):
        main_url = obj.get_main_image_url()
        qs = obj.images.all()
        if main_url:
            qs = qs.exclude(image=main_url)
        return ProductImageSerializer(qs, many=True).data
