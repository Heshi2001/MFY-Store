from django.urls import path
from .views import site_page

urlpatterns = [
    path("privacy-policy/", site_page, {"slug": "privacy-policy"}, name="privacy-policy"),
    path("terms-conditions/", site_page, {"slug": "terms-conditions"}, name="terms-conditions"),
    path("refund-policy/", site_page, {"slug": "refund-policy"}, name="refund-policy"),
    path("shipping-policy/", site_page, {"slug": "shipping-policy"}, name="shipping-policy"),
    path("cancellation-policy/", site_page, {"slug": "cancellation-policy"}, name="cancellation-policy"),

    # dynamic fallback for any other page
    path("<slug:slug>/", site_page, name="site_page"),
]
