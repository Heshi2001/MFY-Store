"""
store/services/order_services.py

Production-level business logic for order cancellation, returns,
and time-based status auto-update. Keep views thin — all logic lives here.
"""

from __future__ import annotations

from datetime import timedelta
from django.utils import timezone
from django.db import transaction

# ─────────────────────────────────────────────
# STATUS CONSTANTS
# ─────────────────────────────────────────────

CANCELLABLE_STATUSES = {"Pending", "Processing"}
RETURN_WINDOW_DAYS = 7

# Maps status → (min_hours_since_order, progress_pct)
STATUS_TIMELINE = [
    ("Pending",          0,    20),
    ("Processing",       1,    40),
    ("Shipped",          6,    60),
    ("Out for Delivery", 24,   80),
    ("Delivered",        72,  100),
]


# ─────────────────────────────────────────────
# 1. AUTO STATUS UPDATE  (time-based, realistic)
# ─────────────────────────────────────────────

def update_order_status(order) -> bool:
    """
    Advance order.status based on elapsed time since order.created_at.
    Only moves FORWARD — never overrides Cancelled / Returned.
    Returns True if the status was changed and saved.
    """
    # Never touch terminal statuses
    if order.status in {"Cancelled", "Returned", "Refunded"}:
        return False

    now = timezone.now()
    elapsed_hours = (now - order.created_at).total_seconds() / 3600

    new_status = order.status
    for status, min_hours, _ in STATUS_TIMELINE:
        if elapsed_hours >= min_hours:
            new_status = status

    if new_status != order.status:
        order.status = new_status

        # Record delivered_at automatically
        if new_status == "Delivered" and not order.delivered_at:
            order.delivered_at = now

        order.save(update_fields=["status", "delivered_at"])
        return True

    return False


# ─────────────────────────────────────────────
# 2. CANCEL ORDER
# ─────────────────────────────────────────────

@transaction.atomic
def cancel_order(order, user) -> dict:
    """
    Cancel an order owned by `user`.

    Returns:
        {"success": True} or {"success": False, "error": "..."}
    """
    # Security: ownership check
    if order.user_id != user.id:
        return {"success": False, "error": "Permission denied."}

    if order.status not in CANCELLABLE_STATUSES:
        return {
            "success": False,
            "error": f"Cannot cancel an order that is '{order.status}'.",
        }

    # ── Restore stock ──────────────────────────────
    for item in order.items.select_related("product", "variant"):
        if item.dealer == "Self":
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save(update_fields=["stock"])
            else:
                item.product.stock = getattr(item.product, "stock", 0) + item.quantity
                item.product.save(update_fields=["stock"])

    # ── Update order ───────────────────────────────
    now = timezone.now()
    order.status = "Cancelled"
    order.cancelled_at = now
    order.save(update_fields=["status", "cancelled_at"])

    # ── Refund payment if paid ─────────────────────
    try:
        payment = order.payment  # OneToOne reverse
        if payment.status == "PAID":
            payment.status = "REFUNDED"
            payment.refunded_at = now
            payment.save(update_fields=["status", "refunded_at"])
            order.payment_status = "REFUNDED"
            order.save(update_fields=["payment_status"])
    except Exception:
        pass  # No payment record; COD or not yet created

    return {"success": True}


# ─────────────────────────────────────────────
# 3. REQUEST RETURN
# ─────────────────────────────────────────────

def request_return(order, user, reason: str, items_data: list | None = None) -> dict:
    """
    Create a ReturnRequest for a delivered order within the return window.

    items_data: optional list of {"order_item_id": int, "quantity": int}
    """
    from store.models import ReturnRequest  # local import to avoid circular

    if order.user_id != user.id:
        return {"success": False, "error": "Permission denied."}

    if order.status != "Delivered":
        return {"success": False, "error": "Only delivered orders can be returned."}

    if not order.delivered_at:
        # Fallback: treat estimated_delivery as delivered_at
        return {"success": False, "error": "Delivery not yet confirmed."}

    window_end = order.delivered_at + timedelta(days=RETURN_WINDOW_DAYS)
    if timezone.now() > window_end:
        return {"success": False, "error": "Return window has expired (7 days after delivery)."}

    if ReturnRequest.objects.filter(order=order, user=user).exists():
        return {"success": False, "error": "A return request already exists for this order."}

    ret = ReturnRequest.objects.create(
        order=order,
        user=user,
        reason=reason,
        status="Requested",
    )

    return {"success": True, "return_id": ret.id}


# ─────────────────────────────────────────────
# 4. APPROVE RETURN  (admin / staff action)
# ─────────────────────────────────────────────

def approve_return(return_request, staff_user) -> dict:
    if not staff_user.is_staff:
        return {"success": False, "error": "Staff only."}

    if return_request.status != "Requested":
        return {"success": False, "error": "Only 'Requested' returns can be approved."}

    return_request.status = "Approved"
    return_request.approved_at = timezone.now()
    return_request.save(update_fields=["status", "approved_at"])

    return {"success": True}


# ─────────────────────────────────────────────
# 5. COMPLETE RETURN  (admin / staff action)
# ─────────────────────────────────────────────

@transaction.atomic
def complete_return(return_request, staff_user) -> dict:
    if not staff_user.is_staff:
        return {"success": False, "error": "Staff only."}

    if return_request.status not in {"Approved", "Picked"}:
        return {"success": False, "error": "Return must be Approved or Picked first."}

    now = timezone.now()
    return_request.status = "Completed"
    return_request.completed_at = now
    return_request.save(update_fields=["status", "completed_at"])

    order = return_request.order
    order.status = "Returned"
    order.returned_at = now
    order.save(update_fields=["status", "returned_at"])

    # Mark payment as refunded
    try:
        payment = order.payment
        payment.status = "REFUNDED"
        payment.refunded_at = now
        payment.save(update_fields=["status", "refunded_at"])
        order.payment_status = "REFUNDED"
        order.save(update_fields=["payment_status"])
    except Exception:
        pass

    return {"success": True}
