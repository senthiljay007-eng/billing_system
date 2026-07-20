from django.urls import path

from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.bill_create_view, name='bill_create'),
    path('invoice/<int:invoice_id>/', views.invoice_detail_view, name='invoice_detail'),
    path('purchases/', views.customer_purchases_view, name='customer_purchases'),
    path('products/lookup/', views.product_lookup_view, name='product_lookup'),
]
