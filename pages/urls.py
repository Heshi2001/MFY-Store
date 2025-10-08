from django.urls import path
from . import views

urlpatterns = [
    path('refund/', views.refund, name='refund'),
    path('shipping/', views.shipping, name='shipping'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
]
