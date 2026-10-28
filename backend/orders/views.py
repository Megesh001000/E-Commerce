import json 

from decimal import Decimal

from django.db import transaction,IntegrityError
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status 
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.parsers import BaseParser


from cart.models import Cart
from products.models import Product
from .models import Order,OrderItem,WebhookEvent,DeliveryAddress
from .serializers import OrderSerializer,OrderItemSerializer,DeliveryAddressSerializer
from .services import create_razorpay_order,get_razorpay_client,process_captured_payment,confirm_captured_payment

class CheckOutView(APIView):
    permission_classes=[IsAuthenticated]

    @transaction.atomic
    def post(self,request):

        try:
            cart=Cart.objects.select_for_update().get(user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {"error":"Your Cart is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_items=list(
            cart.items.select_related("product").all()
        )
        if not cart_items:
            return Response(
                {"error": "Your cart is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

       
        locked_products={}
        total_amount=Decimal(0.00)

        for cart_item in cart_items: #Lock product rows and validate stock.
            product=Product.objects.select_for_update().get(
                id=cart_item.product_id
            )

            if product.stock < cart_item.quantity:
                 return Response(
                    {
                        "error": (
                            f"Insufficient stock for {product.name}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            locked_products[product.id] = product
            total_amount+=product.price * cart_item.quantity

        order=Order.objects.create(       # Create ONE order for the entire cart.
            user=request.user,
            total_amount=total_amount,
            status=Order.Status.PENDING,
            stock_reserved=True
        )
        order_items=[]   # Save purchase details and reserve the stock.
                

        for cart_item in cart_items:
            product = locked_products[cart_item.product_id]

            order_items.append(
                OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    price=product.price,
                    quantity=cart_item.quantity,
                )
            )

            product.stock-=cart_item.quantity
            product.save(update_fields=["stock"])
        

        OrderItem.objects.bulk_create(order_items)
        # Empty the cart so the same items aren't checked out again.
        cart.items.all().delete()

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )

class CancelOrderView(APIView):
    permission_classes=[IsAuthenticated]

    @transaction.atomic
    def post(self,request,order_id):
        order=get_object_or_404(
            Order.objects.select_for_update(),
            id=order_id,
            user=request.user
        )

        if order.status != Order.Status.PENDING:
            return Response(
                {"error": "Only pending orders can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.stock_reserved:
            order_items=list(
                order.items.select_related("product").all()
            )

            for item in order_items:
                product=Product.objects.select_for_update().get(
                    id=item.product_id
                )
                product.stock+=item.quantity
                product.save(update_fields=["stock"])

            order.stock_reserved=False

        order.status=Order.Status.CANCELLED
        order.save(update_fields=["status","stock_reserved","updated_at"])


        return Response(
            {
                "message":"Order cancelled and reserved stock restored.",
                "order_id":str(order_id),
                "status":order.status,
            },
            status=status.HTTP_200_OK

        )


class CreateRazorpayOrderView(APIView):
    permission_classes=[IsAuthenticated]

    def post(self,request,order_id):

        with transaction.atomic():
            order=get_object_or_404(
                Order.objects.select_for_update(),
                id=order_id,
                user=request.user
            )

            if order.status != Order.Status.PENDING:
                return Response(
                    {"error":"This order is not pending."},
                    status=status.HTTP_400_BAD_REQUEST,

                )

            if not order.stock_reserved:
                return Response(
                    {"error":"Stock is not reserved for this order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if order.payment_status != "pending":
                return Response(
                    {"error":"This order cannot accept a new payment."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                if not order.razorpay_order_id:
                    razorpay_order=create_razorpay_order(order)
                else:
                    razorpay_order={
                        "id":order.razorpay_order_id,
                        "amount":int(order.total_amount*100),
                        "currency":"INR"
                    }
            except Exception:
                return Response(
                    {"error": "Unable to create payment order. Please try again."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        return Response(
            {
                "key_id":settings.RAZORPAY_KEY_ID,
                "razorpay_order_id":razorpay_order["id"],
                "amount":razorpay_order["amount"],
                "currency":razorpay_order["currency"],
                "order_id":str(order_id),
            },
            status=status.HTTP_200_OK
        )



class VerifyRazorpayPaymentView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request,order_id):
        razorpay_order_id=request.data.get("razorpay_order_id")
        payment_id=request.data.get("razorpay_payment_id")
        signature=request.data.get("razorpay_signature")

        if not all([razorpay_order_id,payment_id,signature]):
            return Response(
                {"error":"All payment verification fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order=get_object_or_404(
            Order,
            id=order_id,
            user=request.user
        )

        if order.razorpay_order_id !=razorpay_order_id:
            return Response(
                {"error": "Payment order does not match."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (    # Allow a safe retry after the same payment was confirmed.
            order.payment_status=="captured" and  order.razorpay_payment_id == payment_id
        ):
            return Response(
                {"message": "Payment already confirmed.",
                 "order_id": str(order.id)},
                status=status.HTTP_200_OK,
            )
        # if  (
        #     order.status !=Order.Status.PENDING 
        #     or not order.stock_reserved
        #     or order.payment_status != "pending"
        # ):
        #     return Response(
        #         {"error": "This order cannot be verified for payment."},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )

        client=get_razorpay_client()

        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature":signature,
            })
            payment=client.payment.fetch(payment_id)
        except Exception:
            return Response(
                {"error": "Payment verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        

        if (
            payment.get("order_id") !=razorpay_order_id
            or payment.get("status") != "captured"
            or payment.get("amount") != int(order.total_amount*100)
            or payment.get("currency") != "INR"
        ):
            
            return Response(
                {"error": "Payment is not confirmed as captured."},
                status=status.HTTP_409_CONFLICT,
            )
        try:

            with transaction.atomic():
                locked_order=get_object_or_404(
                    Order.objects.select_for_update(),
                    id=order_id,
                    user=request.user

                )
                if (
                    locked_order.payment_status == "captured"
                    and locked_order.razorpay_payment_id == payment_id
                    and locked_order.razorpay_order_id == razorpay_order_id
                ):
                        return Response(
                                {
                                    "message": "Payment already confirmed.",
                                    "order_id": str(locked_order.id),
                                },
                                status=status.HTTP_200_OK,
                            )

                if  locked_order.razorpay_order_id !=razorpay_order_id:
                     return Response(
                        {"error": "Payment order does not match."},
                        status=status.HTTP_409_CONFLICT,
                    )
                if locked_order.status ==Order.Status.CANCELLED:
                    result=confirm_captured_payment(locked_order,payment_id)
                elif(
                    locked_order.status != Order.Status.PENDING
                    or not locked_order.stock_reserved
                    or locked_order.payment_status != "pending"
                ):
                    return  Response(
                        {"error": "Order state changed. Please check the order."},
                        status=status.HTTP_409_CONFLICT,
                    )
                else:
                    result= confirm_captured_payment(locked_order,payment_id)

                

                # locked_order.razorpay_payment_id=payment_id
                # locked_order.payment_status="captured"
                # locked_order.status=Order.Status.CONFIRMED
                # locked_order.stock_reserved=False

                # locked_order.save(
                #     update_fields=[
                #         "razorpay_payment_id",
                #         "payment_status",
                #         "status",
                #         "stock_reserved",
                #         "updated_at",
                #     ]
                # )
        except  IntegrityError:
            return Response(
                {
                    "error": (
                        "This payment conflicts with an existing record. "
                        "Please check your order status."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        if result == "payment_conflict":
            return Response(
                {
                    "error": "This payment conflicts with an existing record.",
                    "reconciliation_required": True,
                },
                status=status.HTTP_409_CONFLICT,
        )
        if result=="reconciliation_required":
            return Response(
                {
                    "message":(
                        "Payment was captured, but the order is cancelled."
                        "Reconciliation is required."
                    ),
                    "order_id":str(order_id),
                    "payment_status":"captured",
                    "order_status":"cancelled",
                    "requires_reconciliation":True

                },
                status=status.HTTP_409_CONFLICT
            )
        return Response(
            {
                "message":(
                    "Payment already confirmed."
                    if result=="already_processed"
                    else "Payment verified and order confirmed."
                ),
                "order_id":str(order_id),
                "payment_status":"captured",
                "order_status":(
                    "confirmed"
                    if result in ("confirmed","already_processed")
                    else "cancelled"
                )

            },
            status=status.HTTP_200_OK
        )


class RazorpayWebhookView(APIView):
        permission_classes=[AllowAny]
        authentication_classes=[]
        parser_classes=[]

        def post(self,request):
            signature=request.headers.get("X-Razorpay-Signature")
            event_id=request.headers.get("X-Razorpay-Event-Id")

            if (not signature or not isinstance(event_id,str) or not event_id.strip() or   len(event_id) > 100):
                return Response(
                    {"event":"Missing webhook signature or event ID"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not settings.RAZORPAY_WEBHOOK_SECRET:
                return Response(
                    {"error":"Webhook configuration is missing."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            raw_body=request.body

            try:  #verify signature against with original,unmodified request body
                client=get_razorpay_client()
                client.utility.verify_webhook_signature(
                    raw_body.decode("utf-8"),
                    signature,
                    settings.RAZORPAY_WEBHOOK_SECRET,
                )
            except Exception:
                return Response(
                    {"error":"Invalid webhook signature."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            try:
                event_data=json.loads(raw_body)
            except (json.JSONDecodeError,UnicodeDecodeError):
                return Response(
                    {"error":"Invalid JSON payload"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not isinstance(event_data, dict):
                return Response(
                    {"error": "Webhook payload must be a JSON object."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            event_type=event_data.get("event")

            if not isinstance(event_type,str) or not event_type:
                return Response(
                    {"error": "Missing event type."},
                    status=status.HTTP_400_BAD_REQUEST,
            )

            try:
                with transaction.atomic():
                    webhook_event,created=WebhookEvent.objects.get_or_create(
                        event_id=event_id,
                        defaults={
                            "event_type":event_type,
                            "payload":event_data,
                        },
                    )
            except IntegrityError:
                # A concurrent request may have inserted the same event.
                webhook_event=WebhookEvent.objects.get(event_id=event_id)
                created=False

            # if not created and webhook_event.processed:
            #         return Response(
            #             {"message": "Event already processed."},
            #             status=status.HTTP_200_OK,
            #         )
         
            try:
                with transaction.atomic():
                    locked_event=WebhookEvent.objects.select_for_update().get(
                        event_id=event_id
                    )
                    if locked_event.processed:
                            return Response(
                                {"message": "Event already processed."},
                                status=status.HTTP_200_OK,
                            )
                    if (locked_event.event_type != event_type or locked_event.payload != event_data):
                            return Response(
                                {"error": "Event ID conflicts with saved event."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                    if locked_event.event_type == "payment.captured":
                            result=process_captured_payment(locked_event.payload)
                            if result == "payment_conflict":
                                locked_event.reconciliation_required = True
                                locked_event.processing_error=(
                                        "Payment ID is already assigned to another order."
                                    )
                                locked_event.processed=True
                                locked_event.processed_at=timezone.now()
                                locked_event.save(update_fields=["processed", "processed_at","reconciliation_required","processing_error"])
                                return Response(
                                    {
                                        "message": "Payment conflict recorded for reconciliation.",
                                        "reconciliation_required": True,
                                    },
                                    status=status.HTTP_200_OK,
                                )
                            if result=="reconciliation_required":
                                locked_event.reconciliation_required=True
                                locked_event.processing_error=(
                                     "Payment captured for a cancelled order."
                                )
                    locked_event.processed = True
                    locked_event.processed_at = timezone.now()
                    locked_event.save(
                        update_fields=[
                            "processed",
                            "processed_at",
                            "reconciliation_required",
                            "processing_error",
                        ]
                    )
            except ValueError as exc:
                print("DEBUG webhook ValueError:", repr(exc))
                return Response(
                    {"error": "Payment event could not be reconciled."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )   
                    
               
            except Exception:
                 return Response(
                    {"error": "Webhook processing failed. Please retry."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return Response(
                            {"message": "Webhook received and handled."},
                            status=status.HTTP_200_OK,
                        )

class DeliveryAddressListCreateView(generics.ListCreateAPIView):
    serializer_class=DeliveryAddressSerializer
    permission_classes=[IsAuthenticated]

    def get_queryset(self):
        return DeliveryAddress.objects.filter(
            user=self.request.user
        )
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class DeliveryAddressDetailView(generics.RetrieveUpdateDestroyAPIView):

    serializer_class=DeliveryAddressSerializer
    permission_classes=[IsAuthenticated]
    def get_queryset(self):
        return DeliveryAddress.objects.filter(
            user=self.request.user
        )

            


            
        
