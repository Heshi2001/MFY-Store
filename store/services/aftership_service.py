"""
store/services/aftership_service.py

Handles AfterShip API — register AWB, receive webhooks.
Free tier: 50 shipments/month
Sign up: https://www.aftership.com → get API key → add to .env
"""

import requests
from django.conf import settings

AFTERSHIP_BASE = "https://api.aftership.com/tracking/2024-10"


def _headers():
    return {
        "as-api-key":    settings.AFTERSHIP_API_KEY,
        "Content-Type":  "application/json",
    }


# Aftership tag → your order status
AFTERSHIP_TAG_MAP = {
    "Pending":        "Processing",
    "InfoReceived":   "Processing",
    "InTransit":      "Shipped",
    "OutForDelivery": "Out for Delivery",
    "Delivered":      "Delivered",
    "FailedAttempt":  "Shipped",
    "Exception":      "Shipped",
    "Expired":        "Shipped",
}


def register_tracking(awb_number: str, order_id: int, courier_slug: str | None = None) -> dict:
    """
    Tell AfterShip to start tracking this AWB.
    courier_slug = None → AfterShip auto-detects the courier.

    Indian courier slugs for reference:
      dtdc | delhivery | xpressbees | bluedart | ekart | shiprocket
    """
    if not settings.AFTERSHIP_API_KEY:
        print("[AfterShip] No API key configured — skipping registration")
        return {}

    payload = {
        "tracking": {
            "tracking_number": awb_number,
            "order_id":        str(order_id),
        }
    }

    # Only add slug if known — otherwise AfterShip auto-detects
    if courier_slug:
        payload["tracking"]["slug"] = courier_slug

    try:
        resp = requests.post(
            f"{AFTERSHIP_BASE}/trackings",
            json=payload,
            headers=_headers(),
            timeout=10,
        )
        return resp.json()
    except Exception as e:
        print(f"[AfterShip] register_tracking failed: {e}")
        return {}


def get_tracking(awb_number: str) -> dict:
    """Fetch current tracking info from AfterShip."""
    try:
        resp = requests.get(
            f"{AFTERSHIP_BASE}/trackings",
            params={"tracking_numbers": awb_number},
            headers=_headers(),
            timeout=10,
        )
        return resp.json()
    except Exception as e:
        print(f"[AfterShip] get_tracking failed: {e}")
        return {}