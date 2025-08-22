from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('about/', views.about, name='about'),
    path('products/', views.products_view, name='products'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('contact/', views.contact_view, name='contact'),
    path('contact_thanks/', views.contact_thanks, name='contact_thanks'),
    path('search_results/', views.search_view, name='search_results'),
    path('faq/', views.faq, name='faq'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('add_to_wishlist/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove_from_wishlist/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('submit_review/<int:product_id>/', views.submit_review, name='submit_review'),
    path("otp-login/", views.send_email_otp, name="otp_login"),
    path("verify-email-otp/", views.verify_email_otp, name="verify_email_otp"),
    path("otp-success/", views.otp_success, name="otp_success"),
]
