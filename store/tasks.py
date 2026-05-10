# store/tasks.py
# Uncomment the @shared_task decorator when you add Celery

from store.models import Order, Fulfillment
from store.services.qikink_service import sync_fulfillment_status

# @shared_task           ← uncomment when Celery is set up
def auto_sync_all_qikink_orders():
    """
    Polls Qikink API for every active Qikink order.
    Currently returns None (Qikink GET endpoint not live yet).
    When they add it: remove the 'return None' line in
    qikink_service.poll_qikink_order() and this runs fully.
    """
    active_fulfillments = Fulfillment.objects.filter(
        dealer="Qikink",
    ).exclude(
        order__status__in=["Delivered", "Cancelled", "Returned"]
    )

    updated = 0
    for f in active_fulfillments:
        if sync_fulfillment_status(f):
            updated += 1

    print(f"[Qikink Sync] Updated {updated} fulfillments")
    return updated