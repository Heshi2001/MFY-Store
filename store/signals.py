from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.conf import settings
from .models import Product, ProductVariant, Wishlist, StockNotification, UserProfile

@receiver(post_save, sender=Product)
def notify_price_drop(sender, instance, **kwargs):
    """
    Send a price drop alert to users who enabled alerts on wishlist items.
    """
    try:
        # Find all wishlists for this product with alert enabled
        wishlists = Wishlist.objects.filter(product=instance, alert_enabled=True)

        for wishlist in wishlists:
            user_email = wishlist.user.email
            product_name = instance.name
            new_price = instance.price

            # Simple email notification (you can replace with popup/notification later)
            send_mail(
                subject=f"Price Drop Alert: {product_name}",
                message=(
                    f"Good news! 🎉\n\nThe price of '{product_name}' has dropped!\n"
                    f"New Price: ₹{new_price}\n\n"
                    f"Check it out here: https://yourdomain.com/product/{instance.id}/"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                fail_silently=True,
            )

    except Exception as e:
        print("⚠️ Price drop alert failed:", e)

@receiver(post_save, sender=ProductVariant)
def notify_users_on_restock(sender, instance, created, **kwargs):
    """
    Notify users when a variant comes back in stock (0 → >0).
    """
    if instance.stock <= 0:
        return

    notifications = StockNotification.objects.filter(
        product=instance.product,
        is_notified=False
    )

    for notif in notifications:
        send_mail(
            subject=f"{instance.product.name} is back in stock!",
            message=(
                f"Good news! 🎉\n\n"
                f"{instance.product.name} is now available again at MFY Store.\n"
                f"Variant: {instance.color.name} / {instance.size.name}"
            ),
            from_email="noreply@mfystore.com",
            recipient_list=[notif.user.email],
            fail_silently=True,
        )
        notif.is_notified = True
        notif.save()

# --------------------------------------------------
# USER PROFILE SIGNALS ✅
# --------------------------------------------------

@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, **kwargs):
    UserProfile.objects.get_or_create(user=instance)