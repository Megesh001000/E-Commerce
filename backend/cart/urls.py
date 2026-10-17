from django.urls import path
from .views import CartAPI,CartItemAdd,CartItemUpdate
urlpatterns=[
    path("cart/",CartAPI.as_view(),name="cart-detail"),
    path("cart/items/",CartItemAdd.as_view(),name="cart-item-add"),
    path("cart/items/<int:item_id>/",CartItemUpdate.as_view(),name="cart-item-update")
]
