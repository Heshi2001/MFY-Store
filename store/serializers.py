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
            "id", "color", "size", "age_group", "quantity", "image",
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
    # ✅ Changed images to SerializerMethodField to exclude main image
    images = serializers.SerializerMethodField()
    variants = ProductVariantSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    main_thumbnail_url = serializers.SerializerMethodField()
    main_full_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "sku", "name", "price", "offer_price", "dealer",
            "stock", "description", "category", "images", "variants",
            "main_thumbnail_url", "main_full_url",
        ]

    def get_main_thumbnail_url(self, obj):
        url = obj.get_main_image_url() or (
            obj.images.first().image.url if obj.images.exists() else None
        )
        return normalize_image_url(url, size=400)

    def get_main_full_url(self, obj):
        url = obj.get_main_image_url() or (
            obj.images.first().image.url if obj.images.exists() else None
        )
        return normalize_image_url(url, size=800)

    def get_images(self, obj):
        """
        ✅ Exclude main image from the images list to prevent duplicates
        """
        main_url = obj.get_main_image_url()
        non_main_images = obj.images.all()
        if main_url:
            # Exclude main image
            non_main_images = non_main_images.exclude(image=main_url)

        return ProductImageSerializer(non_main_images, many=True).data
