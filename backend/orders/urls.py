from django.urls import path,include
from .views import CheckOutView,CancelOrderView,CreateRazorpayOrderView,VerifyRazorpayPaymentView,RazorpayWebhookView,DeliveryAddressDetailView,DeliveryAddressListCreateView

urlpatterns=[
    path("checkout/",CheckOutView.as_view(),name="checkout"),
    path("orders/<uuid:order_id>/cancel/",CancelOrderView.as_view(),name="order-cancel"),
    path("orders/<uuid:order_id>/payment",CreateRazorpayOrderView.as_view(),name="create-razorpay-order"),
    path("orders/<uuid:order_id>/verify-payment",VerifyRazorpayPaymentView.as_view(),name="verify-razorpay-payment"),
    path("webhook/razorpay/",RazorpayWebhookView.as_view(),name="razorpay-webhook"),
    path("delivery-addresses/",DeliveryAddressListCreateView.as_view(),name="delivery-address-list-create"),
    path("delivery-addresses/<uuid:pk>/",DeliveryAddressDetailView.as_view(),name="delivery-address-detail-create"),


]