
from decimal import Decimal
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase,override_settings

from rest_framework.test import APIRequestFactory,force_authenticate

from .models import Order, OrderItem,DeliveryAddress
from .services import process_captured_payment
from .models import WebhookEvent
from .views import (
                    RazorpayWebhookView,
                    CheckOutView,CancelOrderView,
                    VerifyRazorpayPaymentView,
                    CreateRazorpayOrderView,
                    DeliveryAddressDetailView,
                    DeliveryAddressListCreateView,
                )
from cart.models import Cart, CartItem
from categories.models import Category
from products.models import Product
User = get_user_model()


class CapturedPaymentServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="payment_test_user",
            password="test-password",
        )

        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("125.00"),
            status=Order.Status.PENDING,
            payment_status="pending",
            stock_reserved=True,
            razorpay_order_id="order_test_123",
        )

    def make_captured_event(
        self,
        payment_id="pay_test_123",
        razorpay_order_id="order_test_123",
        amount=12500,
        currency="INR",
        payment_status="captured",
    ):
        return {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": razorpay_order_id,
                        "amount": amount,
                        "currency": currency,
                        "status": payment_status,
                    }
                }
            },
        }

    def test_successful_payment_confirms_order(self):
        result = process_captured_payment(
            self.make_captured_event()
        )

        self.order.refresh_from_db()

        self.assertEqual(result, "confirmed")
        self.assertEqual(
            self.order.status,
            Order.Status.CONFIRMED,
        )
        self.assertEqual(self.order.payment_status, "captured")
        self.assertEqual(
            self.order.razorpay_payment_id,
            "pay_test_123",
        )
        self.assertFalse(self.order.stock_reserved)
        self.assertFalse(self.order.requires_reconciliation)

    def test_duplicate_payment_is_not_processed_twice(self):
        event = self.make_captured_event()

        first_result = process_captured_payment(event)
        second_result = process_captured_payment(event)

        self.order.refresh_from_db()

        self.assertEqual(first_result, "confirmed")
        self.assertEqual(second_result, "already_processed")
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)
        self.assertEqual(
            self.order.razorpay_payment_id,
            "pay_test_123",
        )

    def test_captured_payment_for_cancelled_order_requires_reconciliation(self):
        self.order.status = Order.Status.CANCELLED
        self.order.stock_reserved = False
        self.order.save(
            update_fields=["status", "stock_reserved"]
        )

        result = process_captured_payment(
            self.make_captured_event()
        )

        self.order.refresh_from_db()

        self.assertEqual(result, "reconciliation_required")
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(self.order.payment_status, "captured")
        self.assertTrue(self.order.requires_reconciliation)

    def test_payment_id_already_used_by_another_order_is_rejected(self):
        other_order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("50.00"),
            status=Order.Status.CONFIRMED,
            payment_status="captured",
            stock_reserved=False,
            razorpay_order_id="order_test_other",
            razorpay_payment_id="pay_shared_123",
        )

        result = process_captured_payment(
            self.make_captured_event(
                payment_id="pay_shared_123"
            )
        )

        self.order.refresh_from_db()
        other_order.refresh_from_db()

        self.assertEqual(result, "payment_conflict")
        self.assertEqual(self.order.payment_status, "pending")
        self.assertIsNone(self.order.razorpay_payment_id)
        self.assertEqual(
            other_order.razorpay_payment_id,
            "pay_shared_123",
        )

    def test_wrong_amount_is_rejected(self):
        with self.assertRaises(ValueError):
            process_captured_payment(
                self.make_captured_event(amount=12499)
            )

        self.order.refresh_from_db()

        self.assertEqual(self.order.payment_status, "pending")
        self.assertEqual(self.order.status, Order.Status.PENDING)

    def test_unknown_razorpay_order_is_rejected(self):
        with self.assertRaises(ValueError):
            process_captured_payment(
                self.make_captured_event(
                    razorpay_order_id="order_unknown_123"
                )
            )

        self.order.refresh_from_db()

        self.assertEqual(self.order.payment_status, "pending")
        self.assertIsNone(self.order.razorpay_payment_id)

@override_settings(RAZORPAY_WEBHOOK_SECRET="test-webhook-secret")
class RazorpayWebhookTests(TestCase):
    def setUp(self):
        self.factory=APIRequestFactory()
        self.view=RazorpayWebhookView.as_view()
    def make_event(self):
        return {
            "event":"payment.captured",
            "payload":{
                "payment":{
                    "entity":{
                        "id":"payment_webhook_test",
                        "order_id":"order_webhook_test",
                        "amount":12500,
                        "currency":"INR",
                        "status":"captured",
                    }
                }
            },
        }

    def make_request(self,event_data,event_id="evt_test_123"):
        return self.factory.post(
            "/webhooks/razorpay/",
            data=json.dumps(event_data),
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE="test_signature",
            HTTP_X_RAZORPAY_EVENT_ID=event_id,

        )

    def test_invalid_signature_is_rejected(self):
        event_data=self.make_event()
        request=self.make_request(event_data)

        with patch("orders.views.get_razorpay_client") as get_client:
            get_client.return_value.utility.verify_webhook_signature.side_effect=(
                 Exception("Invalid signature")
            )
            response=self.view(request)
        self.assertEqual(response.status_code,400)
        self.assertFalse(WebhookEvent.objects.filter(event_id="evt_test_123").exists())

    def test_processed_duplicate_event_is_not_processed_again(self):
        event_data=self.make_event()
        WebhookEvent.objects.create(
            event_id="evt_test_123",
            event_type="payment.captured",
            payload=event_data,
            processed=True,
        )
        request=self.make_request(event_data)
        with(
            patch("orders.views.get_razorpay_client") as get_client,
            patch("orders.views.process_captured_payment") as process_payement
        ):
            get_client.return_value.utility.verify_webhook_signature.return_value=(None)
            response=self.view(request)

        self.assertEqual(
            response.status_code,200
        )
        self.assertEqual(
            response.data["message"],
            "Event already processed.",
        )
        process_payement.assert_not_called()
        self.assertEqual(
            WebhookEvent.objects.filter(event_id="evt_test_123").count(),
            1,
        )
    def test_valid_captured_webhook_confirms_order_and_handles_replay(self):
            User=get_user_model()
            user=User.objects.create_user(
                username="webhook_processing_user",
            password="test-password",
            )
            order=Order.objects.create(
                user=user,
                total_amount=Decimal("125.00"),
                status=Order.Status.PENDING,
                payment_status="pending",
                stock_reserved=True,
                razorpay_order_id="order_webhook_test",
            )
            event_data=self.make_event()
            event_data["payload"]["payment"]["entity"]["order_id"] = (
                "order_webhook_test"
            )
            processing_errors = []

            def debug_process(event_payload):
                try:
                    return process_captured_payment(event_payload)
                except Exception as exc:
                    processing_errors.append(
                        f"{type(exc).__name__}: {exc}"
                    )
                    raise

            with (
                patch("orders.views.get_razorpay_client") as get_client,
                patch(
                    "orders.views.process_captured_payment",
                    side_effect=debug_process,
                ),
            ):
                get_client.return_value.utility.verify_webhook_signature.return_value = None

                response = self.view(
                    self.make_request(
                        event_data,
                        event_id="evt_valid_capture_test",
                    )
                )

            self.assertEqual(
                response.status_code,
                200,
                f"Response: {response.data}; underlying exception: {processing_errors}",
            )
            order.refresh_from_db()
            webhook_event = WebhookEvent.objects.get(
                event_id="evt_valid_capture_test"
            )

            self.assertEqual(order.status, Order.Status.CONFIRMED)
            self.assertEqual(order.payment_status, "captured")
            self.assertEqual(
                order.razorpay_payment_id,
                "payment_webhook_test",
            )
            self.assertFalse(order.stock_reserved)
            self.assertTrue(webhook_event.processed)
            self.assertFalse(webhook_event.reconciliation_required)

            with (
                patch("orders.views.get_razorpay_client") as get_client,
                patch("orders.views.process_captured_payment") as process_payment,
            ):
                get_client.return_value.utility.verify_webhook_signature.return_value=(
                    None
                )
                response=self.view(
                    self.make_request(
                        event_data,
                        event_id="evt_valid_capture_test",
                    )
                )
            self.assertEqual(response.status_code,200)
            self.assertEqual(
                response.data["message"],
                "Event already processed.",
            )
            process_payment.assert_not_called()
            self.assertEqual(
                WebhookEvent.objects.filter(
                    event_id="evt_valid_capture_test"
                ).count(),
                1,
            )
    def  test_captured_payment_for_cancelled_order_records_reconciliation(self):
            user=User.objects.create_user(
                username="cancelled_webhook_test",
                password="test-password"

      
            )
            order=Order.objects.create(
                user=user,
                total_amount=Decimal("125.00"),
                status=Order.Status.CANCELLED,
                payment_status="pending",
                stock_reserved=False,
                razorpay_order_id="order_webhook_test",
            )
            event_data=self.make_event()
            request=self.make_request(
                event_data,
                event_id="evt_cancelled_capture_test",
            )
            with patch("orders.views.get_razorpay_client") as get_client:
                get_client.return_value.utility.verify_webhook_signature.return_value=None
                response=self.view(request)
            order.refresh_from_db()
            webhook_event = WebhookEvent.objects.get(
                event_id="evt_cancelled_capture_test"
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(order.status, Order.Status.CANCELLED)
            self.assertEqual(order.payment_status, "captured")
            self.assertTrue(order.requires_reconciliation)
            self.assertTrue(webhook_event.processed)
            self.assertTrue(webhook_event.reconciliation_required)
    def test_payment_id_conflict_is_recorded_for_reconciliation(self):
        user=User.objects.create_user(
            username="payment_conflict_user",
            password="test-password"
        )
        order = Order.objects.create(
            user=user,
            total_amount=Decimal("125.00"),
            status=Order.Status.PENDING,
            payment_status="pending",
            stock_reserved=True,
            razorpay_order_id="order_webhook_test",
        )

        Order.objects.create(
            user=user,
            total_amount=Decimal("125.00"),
            status=Order.Status.CONFIRMED,
            payment_status="captured",
            stock_reserved=False,
            razorpay_order_id="order_other_webhook",
            razorpay_payment_id="payment_webhook_test",
        )
        event_data=self.make_event()
        resquest=self.make_request(
            event_data,
            event_id="evt_payment_conflict_test",
        )
        with patch("orders.views.get_razorpay_client") as get_client:
            get_client.return_value.utility.verify_razorpay_signature=None

            response=self.view(
                resquest
            )
        order.refresh_from_db()
        webhook_event=WebhookEvent.objects.create(
            event_id="evt_payment_conflict_test",
        )
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.data["reconciliation_required"])
        self.assertEqual(order.payment_status, "pending")
        self.assertIsNone(order.razorpay_payment_id)
        self.assertTrue(webhook_event.processed)
        self.assertTrue(webhook_event.reconciliation_required)

    def test_wrong_amount_and_currency_are_rejected(self):
        user=User.objects.create_user(
            username="Invalid_user",
            password="test-password"
        )
        order=Order.objects.create(
            user=user,
            total_amount=Decimal("125.00"),
            status=Order.Status.PENDING,
            payment_status="pending",
            stock_reserved=True,
            razorpay_order_id="order_webhook_test",
        )
        invalid_events=[
            ("evt_wrong_amount_test", "amount", 12499),
            ("evt_wrong_currency_test", "currency", "USD"),
        ]

        for event_id,field,value in invalid_events:
            with self.subTest(field=field):
                event_data=self.make_event()
                event_data["payload"]["payment"]["entity"][field]=value
                request=self.make_request(
                    event_data,
                    event_id=event_id
                )
                with patch("orders.views.get_razorpay_client") as get_client:
                    get_client.return_value.utility.verify_payment_signature.return_value=None
                    response=self.view(request)
                self.assertEqual(response.status_code, 500)

                webhook_event = WebhookEvent.objects.get(event_id=event_id)
                self.assertFalse(webhook_event.processed)

                order.refresh_from_db()
                self.assertEqual(order.status, Order.Status.PENDING)
                self.assertEqual(order.payment_status, "pending")
                self.assertIsNone(order.razorpay_payment_id)
    def test_unprocessed_webhook_can_be_retried(self):
        user = User.objects.create_user(
            username="webhook_retry_user",
            password="test-password",
        )

        order = Order.objects.create(
            user=user,
            total_amount=Decimal("125.00"),
            status=Order.Status.PENDING,
            payment_status="pending",
            stock_reserved=True,
            razorpay_order_id="order_webhook_test",
        )

        event_data = self.make_event()

        # Simulate an event saved earlier whose processing did not complete.
        WebhookEvent.objects.create(
            event_id="evt_retry_test",
            event_type="payment.captured",
            payload=event_data,
            processed=False,
        )

        request = self.make_request(
            event_data,
            event_id="evt_retry_test",
        )

        with patch("orders.views.get_razorpay_client") as get_client:
            get_client.return_value.utility.verify_webhook_signature.return_value = None
            response = self.view(request)

        order.refresh_from_db()
        webhook_event = WebhookEvent.objects.get(event_id="evt_retry_test")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(order.payment_status, "captured")
        self.assertTrue(webhook_event.processed)
    def test_captured_payment_for_cancelled_order_records_reconciliation(self):
            user=User.objects.create_user(
                username="cancelled_webhook_user",
                password="test-password"
            )
            order=Order.objects.create(
                user=user,
                total_amount=Decimal("125.00"),
                status=Order.Status.CANCELLED,
                payment_status="pending",
                stock_reserved=False,
                razorpay_order_id="order_webhook_test"
                
            )
            event_data=self.make_event()
            request=self.make_request(
                event_data,
                event_id="evt_cancelled_capture_test",
            )
            with patch("orders.views.get_razorpay_client") as  get_client:
                get_client.return_value.utility.verify_webhook_signature.return_value=None
                response=self.view(request)

            order.refresh_from_db()
            webhook_event=WebhookEvent.objects.get(
                event_id="evt_cancelled_capture_test"
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(order.status, Order.Status.CANCELLED)
            self.assertEqual(order.payment_status, "captured")
            self.assertTrue(order.requires_reconciliation)
            self.assertTrue(webhook_event.processed)
            self.assertTrue(webhook_event.reconciliation_required)

    def test_payment_id_conflict_is_recorded_for_reconciliation(self):
        user=User.objects.create_user(
            username="payment_conflict_test",
            password="test-password"
        )
        
        order=Order.objects.create(
            user=user,
            total_amount=Decimal("125.00"),
            status=Order.Status.PENDING,
            payment_status="pending",
            stock_reserved=True,
            razorpay_order_id="order_webhook_test",
        )
        
        Order.objects.create(
            user=user,
            total_amount=Decimal("125.00"),
            status=Order.Status.CONFIRMED,
            payment_status="captured",
            stock_reserved=False,
            razorpay_order_id="order_other_webhook",
            razorpay_payment_id="payment_webhook_test", 
        )
        event_data = self.make_event()
        request = self.make_request(
            event_data,
            event_id="evt_payment_conflict_test",
        )

        with patch("orders.views.get_razorpay_client") as get_client:
            get_client.return_value.utility.verify_webhook_signature.return_value = None
            response = self.view(request)

        order.refresh_from_db()
        webhook_event = WebhookEvent.objects.get(
            event_id="evt_payment_conflict_test"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["reconciliation_required"])
        self.assertEqual(order.payment_status, "pending")
        self.assertIsNone(order.razorpay_payment_id)
        self.assertTrue(webhook_event.processed)
        self.assertTrue(webhook_event.reconciliation_required)

    def test_wrong_amount_and_currency_are_rejected(self):
        user = User.objects.create_user(
            username="invalid_payment_details_user",
            password="test-password",
        )

        order = Order.objects.create(
            user=user,
            total_amount=Decimal("125.00"),
            status=Order.Status.PENDING,
            payment_status="pending",
            stock_reserved=True,
            razorpay_order_id="order_webhook_test",
        )

        invalid_events = [
            ("evt_wrong_amount_test", "amount", 12499),
            ("evt_wrong_currency_test", "currency", "USD"),
        ]

        for event_id, field, value in invalid_events:
            with self.subTest(field=field):
                event_data = self.make_event()
                event_data["payload"]["payment"]["entity"][field] = value

                request = self.make_request(
                    event_data,
                    event_id=event_id,
                )

                with patch("orders.views.get_razorpay_client") as get_client:
                    get_client.return_value.utility.verify_webhook_signature.return_value = None
                    response = self.view(request)

                self.assertEqual(response.status_code, 500)

                webhook_event = WebhookEvent.objects.get(event_id=event_id)
                self.assertFalse(webhook_event.processed)

                order.refresh_from_db()
                self.assertEqual(order.status, Order.Status.PENDING)
                self.assertEqual(order.payment_status, "pending")
                self.assertIsNone(order.razorpay_payment_id)

    def test_unprocessed_webhook_can_be_retried(self):
        user = User.objects.create_user(
            username="webhook_retry_user",
            password="test-password",
        )

        order = Order.objects.create(
            user=user,
            total_amount=Decimal("125.00"),
            status=Order.Status.PENDING,
            payment_status="pending",
            stock_reserved=True,
            razorpay_order_id="order_webhook_test",
        )

        event_data = self.make_event()

        # Simulate an event saved earlier whose processing did not complete.
        WebhookEvent.objects.create(
            event_id="evt_retry_test",
            event_type="payment.captured",
            payload=event_data,
            processed=False,
        )

        request = self.make_request(
            event_data,
            event_id="evt_retry_test",
        )

        with patch("orders.views.get_razorpay_client") as get_client:
            get_client.return_value.utility.verify_webhook_signature.return_value = None
            response = self.view(request)

        order.refresh_from_db()
        webhook_event = WebhookEvent.objects.get(event_id="evt_retry_test")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(order.payment_status, "captured")
        self.assertTrue(webhook_event.processed)

    def test_reused_event_id_with_different_payload_is_rejected(self):
        event_data = self.make_event()

        WebhookEvent.objects.create(
            event_id="evt_payload_conflict_test",
            event_type="payment.captured",
            payload=event_data,
            processed=False,
        )

        changed_event = self.make_event()
        changed_event["payload"]["payment"]["entity"]["amount"] = 12499

        request = self.make_request(
            changed_event,
            event_id="evt_payload_conflict_test",
        )

        with patch("orders.views.get_razorpay_client") as get_client:
            get_client.return_value.utility.verify_webhook_signature.return_value = None
            response = self.view(request)

        webhook_event = WebhookEvent.objects.get(
            event_id="evt_payload_conflict_test"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(webhook_event.payload, event_data)
        self.assertFalse(webhook_event.processed)


class CheckOutAndCancellationTest(TestCase):
    def setUp(self):
        User=get_user_model()
        self.user=User.objects.create_user(
            username="checkout_test_user",
            password="test_password"
        )
        self.other_user=User.objects.create_user(
            username="sam_test_user",
            password="sam123"
        )

        self.factory=APIRequestFactory()
        self.checkout_view=CheckOutView.as_view()
        self.cancel_view=CancelOrderView.as_view()

        self.category=Category.objects.create(name="Checkout Test Category",)
        self.product = Product.objects.create(
            name="Checkout Test Product",
            category=self.category,
            price=Decimal("25.00"),
            stock=10,
        )

    def make_request(self,path,user):
        request=self.factory.post(
            path,
            data={},
            format="json"
        )
        force_authenticate(request,user=user)
        return request
    def make_reserved_order(self,user=None,quantity=2):
        if not user:
            user=self.user

        order=Order.objects.create(
            user=user,
            total_amount=self.product.price*quantity,
            status=Order.Status.PENDING,
            payment_status="pending",
            stock_reserved=True

        ) 
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            price=self.product.price,
            quantity= quantity
        )
        self.product.stock-=quantity
        self.product.save(update_fields=["stock"])
        return order
    def test_checkout_creates_order_and_reserves_stock(self):
        cart=Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2
        )
        request=self.make_request("/checkout/",self.user)
        response=self.checkout_view(request)


        self.assertEqual(response.status_code,201)
        order=Order.objects.get(user=self.user)

        self.product.refresh_from_db()
        cart.refresh_from_db()

        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.payment_status, "pending")
        self.assertEqual(order.total_amount, Decimal("50.00"))
        self.assertTrue(order.stock_reserved)

        self.assertEqual(self.product.stock, 8)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(cart.items.count(), 0)

    def test_checkout_rejects_insufficient_stock(self):
        self.product.stock=1
        self.product.save(update_fields=["stock"])
        cart=Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2
        )
        request = self.make_request("/checkout/", self.user)
        response = self.checkout_view(request)

        self.product.refresh_from_db()
        cart.refresh_from_db()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.product.stock, 1)
        self.assertEqual(cart.items.count(), 1)
        self.assertFalse(
            Order.objects.filter(user=self.user).exists()
        )

    def test_cancellation_restores_reserved_stock(self):
        order=self.make_reserved_order(quantity=2)
        request=self.make_request(
            f"/orders/{order.id}/cancel/",
            self.user
        )
        response=self.cancel_view(request,order_id=order.id)
        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertFalse(order.stock_reserved)
        self.assertEqual(self.product.stock, 10)

    def test_repeated_cancellation_does_not_restore_stock_twice(self):
        order=self.make_reserved_order(quantity=2)
        first_request = self.make_request(
            f"/orders/{order.id}/cancel/",
            self.user,
        )
        first_response=self.cancel_view(first_request,order_id=order.id)
        self.product.refresh_from_db()
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(self.product.stock, 10)
        second_request = self.make_request(
            f"/orders/{order.id}/cancel/",
            self.user,
        )
        second_response=self.cancel_view(second_request,order_id=order.id)
        self.product.refresh_from_db()
        self.assertEqual(second_response.status_code, 400)
        self.assertEqual(self.product.stock, 10)
    def test_user_cannot_cancel_another_users_order(self):
        order = self.make_reserved_order(quantity=2)

        request = self.make_request(
            f"/orders/{order.id}/cancel/",
            self.other_user,
        )
        response = self.cancel_view(request, order_id=order.id)

        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertTrue(order.stock_reserved)
        self.assertEqual(self.product.stock, 8)
   
class VerifyRazorpayPaymentViewTest(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(
            username="verify_payment_test",
            password="test_password"
        )

        self.order=Order.objects.create(
            user=self.user,
            total_amount=Decimal("125.00"),
            status=Order.Status.PENDING,
            payment_status="pending",
            stock_reserved=True,
            razorpay_order_id="order_verify_test",
        )
        self.factory=APIRequestFactory()
        self.view=VerifyRazorpayPaymentView.as_view()

    def make_request(self, payment_id="pay_verify_test"):
        request=self.factory.post(
            f"/orders/{self.order.id}/verify-payment",
            data={
                "razorpay_order_id":"order_verify_test",
                "razorpay_payment_id":payment_id,
                "razorpay_signature":"test-signature"
            },
            format="json"

        ) 
        force_authenticate(request,user=self.user)
        return request

    def successful_payment_data(self):
        return {
            "id":"payment_verify_test",
            "order_id":"order_verify_test",
            "status":"captured",
            "amount":12500,
            "currency":"INR"
        }
    def test_successful_payment_verification_confirms_order(self):
        with patch("orders.views.get_razorpay_client") as get_client:
            client=get_client.return_value
            client.utility.verify_razorpay_signature.return_value=None

            client.payment.fetch.return_value=self.successful_payment_data()
            response=self.view(
                self.make_request(),order_id=self.order.id
            )
            self.order.refresh_from_db()

            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.order.status, Order.Status.CONFIRMED)
            self.assertEqual(self.order.payment_status, "captured")
            self.assertEqual(
                self.order.razorpay_payment_id,
                "pay_verify_test",
            )
            self.assertFalse(self.order.stock_reserved)
            self.assertFalse(self.order.requires_reconciliation)

    def test_invalid_signature_is_rejected(self):
        with patch("orders.views.get_razorpay_client") as get_client:
            client=get_client.return_value
            client.utility.verify_payment_signature.side_effect=Exception("Invalid signature")
            
            response=self.view(
                self.make_request(),order_id=self.order.id
            )
            client.payment.fetch.assert_not_called()
        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertEqual(self.order.payment_status, "pending")
        self.assertIsNone(self.order.razorpay_payment_id)

    def test_payment_amount_mismatch_is_rejected(self):
        payment=self.successful_payment_data()
        payment["amount"]=12499
        with patch("orders.views.get_razorpay_client") as get_client:
            client=get_client.return_value
            client.utility.verify_payment_signature.return_value=None
            client.payment.fetch.return_value=payment

            response=self.view(
                self.make_request(),order_id=self.order.id
            )

        self.order.refresh_from_db()

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertEqual(self.order.payment_status, "pending")

    def test_retry_of_same_confirmed_payment_is_idempotent(self):
        self.order.status=Order.Status.CONFIRMED
        self.order.payment_status="captured"
        self.order.razorpay_payment_id="pay_verify_test"
        self.order.stock_reserved=False
        self.order.save(update_fields=[
            "status",
            "payment_status",
            "razorpay_payment_id",
            "stock_reserved",
        ])
        with patch("orders.views.get_razorpay_client") as get_client:
            response = self.view(
                self.make_request(),
                order_id=self.order.id,
            )

            get_client.assert_not_called()

        self.order.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)
        self.assertEqual(self.order.payment_status, "captured")
        self.assertEqual(
            self.order.razorpay_payment_id,
            "pay_verify_test",
        )

@override_settings(RAZORPAY_KEY_ID="rzp_test_dummy")
class CreateRazorpayOrderViewTest(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(
            username="Sam",
            password="Sam123"
        )
        self.order=Order.objects.create(
            user=self.user,
            total_amount=Decimal("125.00"),
            status=Order.Status.PENDING,
            payment_status="pending",
            stock_reserved=True

        )
        self.factory=APIRequestFactory()
        self.view=CreateRazorpayOrderView.as_view()

    def make_request(self):
        request=self.factory.post(
            f"/orders/{self.order.id}/razerpay-order/",
            data={},
            format="json"
        )
        force_authenticate(request,user=self.user)

        return request

    def test_creates_razorpay_order_successfully(self):
        with patch("orders.services.get_razorpay_client") as get_client:
            get_client.return_value.order.create.return_value={
                "id":"order_created_test",
                "amount":12500,
                "currency":"INR",
            }
            response=self.view(
                self.make_request(),
                order_id=self.order.id
            )
        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["razorpay_order_id"],
            "order_created_test",
        )
        self.assertEqual(response.data["amount"], 12500)
        self.assertEqual(response.data["currency"], "INR")
        self.assertEqual(response.data["key_id"], "rzp_test_dummy")
        self.assertEqual(
            self.order.razorpay_order_id,
            "order_created_test",
        )

    def test_reuses_existing_razorpay_order(self):
        self.order.razorpay_order_id="order_existing_test"
        self.order.save(update_fields=["razorpay_order_id"])
        with patch("orders.services.get_razorpay_client") as get_client:
            response=self.view(
                self.make_request(),
                order_id=self.order.id
            )
            get_client.assert_not_called()
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data["razorpay_order_id"],"order_existing_test",)
        self.assertEqual(response.data["amount"],12500)
    def test_rejects_cancelled_order(self):
        self.order.status=Order.Status.CANCELLED
        self.order.stock_reserved=False
        self.order.save(update_fields=["status","stock_reserved"])

        with patch("orders.services.get_razorpay_client") as get_client:
            response=self.view(
                self.make_request(),
                order_id=self.order.id
            )
            get_client.assert_not_called()
        self.assertEqual(response.status_code,400)
        
    def  test_rejects_order_without_reserved_stock(self):
        self.order.stock_reserved=False
        self.order.save(update_fields=["stock_reserved"])
        with patch("orders.services.get_razorpay_client") as get_client:
            response = self.view(
                self.make_request(),
                order_id=self.order.id,
            )
            get_client.assert_not_called()

        self.assertEqual(response.status_code, 400)


    def  test_razorpay_api_failure_returns_502(self):
        with patch("orders.services.get_razorpay_client") as get_client:
            get_client.return_value.order.create.side_effect=Exception(
                "Simulated Razorpay API failure"
            )
            response=self.view(
                self.make_request(),
                order_id=self.order.id
            )
        self.order.refresh_from_db()

        self.assertEqual(response.status_code, 502)
        self.assertIsNone(self.order.razorpay_order_id)
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertEqual(self.order.payment_status, "pending")
class DeliveryAddressAPITests(TestCase):
    def setUp(self):
        self.factory=APIRequestFactory()

        self.user=User.objects.create_user(
            username="delivery_user",
            password="test-password",
        )
        self.other_user=User.objects.create_user(
            username="other_delivery_user",
            password="test-password",
        )
        self.list_create_view=(DeliveryAddressListCreateView.as_view())
        self.detail_view=DeliveryAddressDetailView.as_view()

    def  valid_address_data(self,**override):
        data={
            "label": "Home",
            "recipient_name": "Megesh",
            "phone": "9876543210",
            "address_line1": "10 Main Street",
            "address_line2": "",
            "locality": "Tambaram",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "postal_code": "600045",
            "country": "India",
            "latitude": "12.924900",
            "longitude": "80.100000",
            "is_default": False,
        }
        data.update(override)
        return data

    def make_address(self,user,**overrides):
        data=self.valid_address_data(**overrides)
        return DeliveryAddress.objects.create(
            user=user,
            **data
        )
    def test_user_can_create_delivery_address(self):
        request=self.factory.post(
            "/delivery-addresses/",
            self.valid_address_data(),
            format="json",
        )
        force_authenticate(request,user=self.user)
        response=self.list_create_view(request)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            DeliveryAddress.objects.filter(user=self.user).count(),
            1,
        )
        address = DeliveryAddress.objects.get(user=self.user)
        self.assertEqual(address.recipient_name, "Megesh")

    def test_user_only_sees_own_address(self):
        self.make_address(self.user)
        self.make_address(
            self.other_user,
            recipient_name="Another person"
        )

        request=self.factory.get("/delivery-addresses/")
        force_authenticate(request,user=self.user)
        response=self.list_create_view(request)

        self.assertEqual(response.status_code, 200)
        addresses=response.data["results"]
        self.assertEqual(len(addresses),1)
        self.assertEqual(
            addresses[0]["recipient_name"],
            "Megesh",
        )
    def test_user_can_update_his_own_address(self):
        address=self.make_address(self.user)
        request=self.factory.patch(
            f"/delivery-addresses/{address.pk}",
            {"label":"Office"},
            format="json"
        )
        force_authenticate(request, user=self.user)

        response = self.detail_view(request, pk=address.pk)

        self.assertEqual(response.status_code, 200)
        address.refresh_from_db()
        self.assertEqual(address.label, "Office")
    def user_can_access_another_user_address(self):
        address=self.make_address(user=self.other_user)
        request = self.factory.get(
            f"/delivery-addresses/{address.pk}/"
        )
        force_authenticate(request, user=self.user)

        response = self.detail_view(request, pk=address.pk)

        self.assertEqual(response.status_code, 404)

    def test_invalid_coordinates_are_rejected(self):
        request = self.factory.post(
            "/delivery-addresses/",
            self.valid_address_data(latitude="120.000000"),
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = self.list_create_view(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            DeliveryAddress.objects.filter(user=self.user).count(),
            0,
        )
    def test_user_cannot_access_another_users_address(self):
        address = self.make_address(user=self.other_user)

        request = self.factory.get(
            f"/delivery-addresses/{address.pk}/"
        )
        force_authenticate(request, user=self.user)

        response = self.detail_view(request, pk=address.pk)

        self.assertEqual(response.status_code, 404)

    def user_can_delete_his_own_address(self):
        address=self.make_address(self.user)
        request=self.factory.delete(
            f"/delivery-addresses/{address.pk}/",
        )
        force_authenticate(request,user=self.user)
        response=self.detail_view(request,pk=address.pk)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            DeliveryAddress.objects.filter(
                pk=address.pk
            ).exists()
        )

    def test_new_default_address_replaces_previous_default(self):
        old_address=self.make_address(self.user,is_default=True)
        request=self.factory.post(
            "/delivery-addresses/",
            self.valid_address_data(
                label="Work",
                address_line1="20 Business Road",
                is_default=True,
            ),
            format="json",
            
        )
        force_authenticate(request,user=self.user)
        response=self.list_create_view(request)
        self.assertEqual(response.status_code, 201)

        old_address.refresh_from_db()
        self.assertFalse(old_address.is_default)

        new_address = DeliveryAddress.objects.get(
            user=self.user,
            address_line1="20 Business Road",
            
        )
        self.assertTrue(new_address.is_default)

        self.assertEqual(
            DeliveryAddress.objects.filter(
                user=self.user,
                is_default=True,
            ).count(),
            1,
        )