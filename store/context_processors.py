from .models import PromoBanner
from django.utils import timezone
from django.db.models import Q  # <-- import Q

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
