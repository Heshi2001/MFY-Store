from django.db import models
from django.utils.text import slugify

# Create your models here.
class SitePage(models.Model):
    PAGE_CHOICES = [
        ("privacy-policy", "Privacy Policy"),
        ("refund-policy", "Refund & Cancellation Policy"),
        ("shipping-policy", "Shipping Policy"),
        ("terms-conditions", "Terms & Conditions")
    ]

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    content = models.TextField(help_text="Use HTML or text")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
