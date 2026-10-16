from django.urls import path
from .views import CartAPI,CartItemAdd
urlpatterns=[
    path("cart/",CartAPI.as_view(),name="cart-detail"),
    path("cart/items/",CartItemAdd.as_view(),name="cart-item-add")
]
