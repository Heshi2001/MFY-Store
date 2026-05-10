# =============================
# DJANGO IMPORTS (GROUPED TOP)
# =============================
from django.contrib.sessions.models import Session
from django.db.models import Q, Min, Case, When, F, Avg, Count
from django.db.models.functions import Coalesce

from rapidfuzz import process, fuzz


# =============================
# SESSION HELPERS
# =============================

def get_or_create_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


# =============================
# SEARCH HELPERS
# =============================

def normalize(text):
    if not text:
        return ""

    return (
        text.lower()
        .replace("'", "")
        .replace("-", "")
        .replace("_", "")
        .strip()
    )


def correct_query(query, vocabulary):
    q = normalize(query)

    match = process.extractOne(
        q,
        vocabulary,
        scorer=fuzz.WRatio
    )

    if match and match[1] > 80:
        return match[0]

    return query


def smart_search(query):
    if not query:
        return Q()

    query = query.strip()
    terms = [normalize(t) for t in query.split() if t]

    q_objects = Q()

    for term in terms:
        q_objects |= (
            Q(name__icontains=term) |
            Q(keywords__icontains=term) |
            Q(category__name__icontains=term) |
            Q(brand__name__icontains=term)
        )

    return q_objects


# =============================
# PRODUCT RANKING (OPTIONAL USE)
# =============================

def rank_products(products, query):
    query_words = [normalize(w) for w in query.split() if w]

    scored = []

    for p in products:
        score = 0

        name = normalize(p.name)
        brand = normalize(p.brand.name) if p.brand else ""
        category = normalize(p.category.name) if p.category else ""
        keywords = normalize(p.keywords) if p.keywords else ""
        description = normalize(p.description) if p.description else ""

        for q in query_words:

            if q in name:
                score += 120

            if name.startswith(q):
                score += 140

            score += fuzz.partial_ratio(q, name) * 0.6

            if q in brand:
                score += 90

            if q in category:
                score += 70

            if q in keywords:
                score += 40

            if q in description:
                score += 10

        if score > 35:
            scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [p for score, p in scored]


# =============================
# 🔥 PRODUCT QUERY PIPELINE (NEW)
# =============================

def get_products_queryset(base_qs, sort=None):
    """
    🔥 Shared optimized product pipeline
    Used by BOTH product page & category page
    """

    qs = base_qs.select_related("category", "brand").prefetch_related(
        "images",
        "variants",
        "reviews"
    )

    # ✅ Price (CHEAPEST variant)
    qs = qs.annotate(
        base_price=Min(
            Case(
                When(variants__offer_price__isnull=False, then=F("variants__offer_price")),
                default=F("variants__price"),
            )
        )
    )

    # ✅ Ratings
    qs = qs.annotate(
        avg_rating=Coalesce(Avg("reviews__rating"), 0.0),
        total_reviews=Count("reviews")
    )

    # ✅ Sorting
    if sort == "low-high":
        qs = qs.order_by("base_price")

    elif sort == "high-low":
        qs = qs.order_by("-base_price")

    elif sort == "rating":
        qs = qs.order_by("-avg_rating")

    else:
        qs = qs.order_by("-id")

    return qs              

# =============================
# FILTER ENGINE (SHARED)
# =============================

def apply_filters(qs, request):

    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    brands = request.GET.getlist("brand")
    rating = request.GET.get("rating")

    if min_price:
        qs = qs.filter(base_price__gte=min_price)

    if max_price:
        qs = qs.filter(base_price__lte=max_price)

    if brands:
        qs = qs.filter(brand__id__in=brands)

    if rating:
        qs = qs.filter(avg_rating__gte=rating)

    return qs