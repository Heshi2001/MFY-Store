from .models import PromoBanner, Category
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
    categories = Category.objects.filter(parent=None)
    return {'sidebar_categories': categories}
    
def global_cart_and_wishlist_counts(request):
    cart_items_count = 0
    wishlist_ids = []

    try:
        if request.user.is_authenticated:
            # Get cart for logged-in user
            cart_data = Cart.objects.for_user_or_session(user=request.user)
            wishlist_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
        else:
            # Get cart for guest session
            session_key = get_or_create_session_key(request)
            cart_data = Cart.objects.for_user_or_session(session_key=session_key)

        cart_items_count = cart_data["cart"].items.aggregate(total=Sum("quantity"))["total"] or 0
    except Exception:
        pass  # avoid breaking if cart isn't initialized yet

    return {
        'cart_items_count': cart_items_count,
        'wishlist_ids': wishlist_ids,
    }
