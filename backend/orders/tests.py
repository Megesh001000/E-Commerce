
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Order
from .services import process_captured_payment


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
