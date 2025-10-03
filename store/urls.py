from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import CustomPasswordChangeView, account_dashboard

urlpatterns = [
    path('', views.index, name='index'),
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:item_id>/", views.update_cart, name="update_cart"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("order-success/", views.order_success, name="order_success"),
    path('about/', views.about, name='about'),
    path('products/', views.products_view, name='products'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('contact/', views.contact_view, name='contact'),
    path('contact_thanks/', views.contact_thanks, name='contact_thanks'),
    path('search_results/', views.search_view, name='search_results'),
    path("search-suggestions/", views.search_suggestions, name="search_suggestions"),
    path('faq/', views.faq, name='faq'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('add_to_wishlist/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove_from_wishlist/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('submit_review/<int:product_id>/', views.submit_review, name='submit_review'),
    path('otp-login/', views.send_email_otp, name='otp_login'),
    path('verify-email-otp/', views.verify_email_otp, name='verify_email_otp'),
    path('otp-success/', views.otp_success, name='otp_success'),
    path('account/dashboard/', views.account_dashboard, name='account_dashboard'),
    path("account/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("account/settings/", views.account_settings, name="account_settings"),
    path("account/addresses/", views.addresses, name="account_addresses"),
    path("account/addresses/add/", views.address_add, name="address_add"),
    path("account/addresses/<int:pk>/edit/", views.edit_address, name="edit_address"),
    path("account/addresses/<int:pk>/delete/", views.delete_address, name="delete_address"),
    path("account/payments/", views.payments, name="payments"),
    path("account/password/change/", CustomPasswordChangeView.as_view(), name="account_change_password"),
    path("account/offers/", views.account_offers, name="account_offers"),
    path("checkout/", views.checkout, name="checkout"),
    path("payment/success/", views.payment_success, name="payment_success"),
    path("account/orders/", views.orders_list, name="orders"),
    path("account/orders/<int:order_id>/", views.order_detail, name="order_detail"),

]
