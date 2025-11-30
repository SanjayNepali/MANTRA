from django.urls import path
from . import views

urlpatterns = [
    # Merchandise list & create
    path('', views.MerchandiseListView.as_view(), name='merchandise_list'),
    path('create/', views.create_merchandise, name='create_merchandise'),

    # Cart (must come BEFORE <slug:slug>)
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/remove/<uuid:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<uuid:product_id>/', views.update_cart_quantity, name='update_cart_quantity'),

    # Checkout & orders
    path('checkout/', views.checkout, name='checkout'),
    path('order/<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('my-orders/', views.my_orders, name='my_orders'),

    # Detail & add to cart (keep last!)
    path('<slug:slug>/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('<slug:slug>/', views.MerchandiseDetailView.as_view(), name='merchandise_detail'),
]
