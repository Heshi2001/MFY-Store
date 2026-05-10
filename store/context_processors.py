from .models import PromoBanner, Category, Brand
from django.utils import timezone
from django.db.models import Q  # <-- import Q
from django.db.models import Sum
from .models import Cart, Wishlist
from .utils import get_or_create_session_key  # adjust import path if needed

def promo_banner(request):
    now = timezone.now()
    banner = (
        PromoBanner.objects.filter(is_active=True)
        .filter(Q(start_date__lte=now) | Q(start_date__isnull=True))
        .filter(Q(end_date__gte=now) | Q(end_date__isnull=True))
        .order_by('-created_at')
        .first()
    )
    return {"promo_banner_text": banner.message if banner else ""}

def sidebar_categories(request):
    return {
        'sidebar_categories': Category.objects.filter(
            parent__isnull=True
        ).prefetch_related('children')  # ← only this, no cache_tree_children
    }


def sidebar_brands(request):
    return {
        'sidebar_brands': Brand.objects.filter(
            parent__isnull=True,
            is_active=True
        ).prefetch_related('children').order_by("name")
    }

def global_cart_and_wishlist_counts(request):
    cart_items_count = 0
    wishlist_ids = []

    try:
        if request.user.is_authenticated:
            cart_data = Cart.objects.for_user_or_session(user=request.user)

            # ✅ FIX: force evaluation
            wishlist_ids = list(
                Wishlist.objects
                .filter(user=request.user)
                .values_list('product_id', flat=True)
            )

        else:
            session_key = get_or_create_session_key(request)
            cart_data = Cart.objects.for_user_or_session(session_key=session_key)

        cart_items_count = cart_data["cart"].items.aggregate(
            total=Sum("quantity")
        )["total"] or 0

    except Exception:
        pass

    return {
        'cart_items_count': cart_items_count,
        'wishlist_ids': wishlist_ids,  # now a real list ✅
    }
