from django.urls import path

from .views import AdminOrderListView,AdminOrderDetailView,FulfillmentStatusUpdateView

app_name="staff_orders"

urlpatterns=[
    path("",AdminOrderListView.as_view(),name="order-list"),
    path("<str:pk>/",AdminOrderDetailView.as_view(),name="order-detail"),
    path("<str:pk>/fulfillment/",FulfillmentStatusUpdateView.as_view(),name="order-fulfillment-update"),
]