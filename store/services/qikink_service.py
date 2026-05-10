"""
store/services/qikink_service.py

Handles all Qikink API communication.
- Token management (auto-refresh, cached)
- Create order
- Poll order status (ready for when Qikink adds GET endpoint)
"""

import requests
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

BASE = settings.QIKINK_BASE_URL  # https://api.qikink.com


# ─────────────────────────────────────────────
# AUTH — auto-cached token
# ─────────────────────────────────────────────

def get_access_token() -> str:
    """
    Returns valid Qikink access token.
    Caches for 55 min (token expires in 60 min).
    """
    cached = cache.get("qikink_token")
    if cached:
        return cached

    resp = requests.post(
        f"{BASE}/api/token",
        data={
            "ClientId":      settings.QIKINK_CLIENT_ID,
            "client_secret": settings.QIKINK_CLIENT_SECRET,
        },
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json()["Accesstoken"]
    cache.set("qikink_token", token, timeout=55 * 60)
    return token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type":  "application/json",
    }


# ─────────────────────────────────────────────
# GENERIC HELPERS
# ─────────────────────────────────────────────

def qikink_get(endpoint: str) -> dict:
    resp = requests.get(f"{BASE}{endpoint}", headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def qikink_post(endpoint: str, data: dict) -> dict:
    resp = requests.post(f"{BASE}{endpoint}", json=data, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


# ─────────────────────────────────────────────
# QIKINK STATUS → YOUR ORDER STATUS MAP
# ─────────────────────────────────────────────

QIKINK_TO_ORDER_STATUS = {
    "On Hold":              "Processing",
    "Live":                 "Processing",
    "Live OOS":             "Processing",
    "To be Printed":        "Processing",
    "Partially Picklisted": "Processing",
    "Printed":              "Processing",
    "Manifested":           "Processing",
    "In-Transit":           "Shipped",
    "Exception":            "Shipped",
    "Delivered":            "Delivered",
    "RTO Initiated":        "Shipped",
    "Returned":             "Returned",
    "Cancelled":            "Cancelled",
}


# ─────────────────────────────────────────────
# AUTOMATIC POLLING
# (ready now — plug in endpoint when Qikink adds it)
# ─────────────────────────────────────────────

def poll_qikink_order(fulfillment) -> dict | None:
    """
    Fetch latest status + AWB for a fulfillment from Qikink API.

    ⚠️  Qikink hasn't exposed GET /orders/{id} yet.
    ⚠️  When they do, just fill in the correct endpoint below.
    ⚠️  Everything else (mapping, saving) works automatically.

    Returns dict with keys: status, awb, courier  OR  None on failure.
    """

    if not fulfillment.dealer_order_id:
        return None

    try:
        # ── SWAP THIS ENDPOINT when Qikink exposes it ────────────
        # Current: not available yet → returns None gracefully
        # Future:  data = qikink_get(f"/api/orders/{fulfillment.dealer_order_id}")
        # ─────────────────────────────────────────────────────────

        # Remove this return None and uncomment above when ready
        return None

        qikink_status = data.get("status")
        awb           = data.get("tracking_id") or data.get("awb")
        courier       = data.get("courier") or data.get("courier_name")

        return {
            "status":  QIKINK_TO_ORDER_STATUS.get(qikink_status),
            "awb":     awb,
            "courier": courier,
            "raw":     data,
        }

    except Exception as e:
        print(f"[Qikink] poll failed for fulfillment {fulfillment.id}: {e}")
        return None


# ─────────────────────────────────────────────
# SYNC ORDER STATUS FROM QIKINK
# (call from Celery task or view)
# ─────────────────────────────────────────────

def sync_fulfillment_status(fulfillment) -> bool:
    """
    Polls Qikink, updates fulfillment + order status + registers
    AWB with AfterShip if newly available.
    Returns True if anything changed.
    """
    result = poll_qikink_order(fulfillment)
    if not result:
        return False

    changed = False
    order   = fulfillment.order

    # Update fulfillment status
    if result["status"] and fulfillment.status != result["status"]:
        fulfillment.status = result["status"]
        changed = True

    # Save AWB if newly received
    if result["awb"] and not fulfillment.tracking_id:
        fulfillment.tracking_id  = result["awb"]
        fulfillment.courier_name = result.get("courier")
        fulfillment.raw_response = result["raw"]
        changed = True

        # Auto-register with AfterShip when AWB appears
        from store.services.aftership_service import register_tracking
        register_tracking(
            awb_number   = result["awb"],
            order_id     = order.id,
            courier_slug = None,   # AfterShip auto-detects courier
        )
        fulfillment.aftership_registered = True

    if changed:
        fulfillment.save()

    # Update order status
    new_order_status = QIKINK_TO_ORDER_STATUS.get(result["status"])
    if new_order_status and order.status != new_order_status:
        order.status = new_order_status
        if new_order_status == "Delivered" and not order.delivered_at:
            order.delivered_at = timezone.now()
        order.save(update_fields=["status", "delivered_at"])

    return changed