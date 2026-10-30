from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Order,OrderEmailNotification

from .fulfillment_services import update_order_fulfillment_status

User=get_user_model()

class FulfillmentServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="fulfillment_test_user",
            email="customer@example.com",
            password="test-password",
        )

        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("125.00"),
            status=Order.Status.CONFIRMED,
            payment_status="captured",
            stock_reserved=False,
        )
    def assert_valid_transitions(self,current_status,new_status,notification_type):
        self.order.fulfillment_status=current_status
        self.order.save(update_fields=["fulfillment_status"])
        with patch("orders.fulfillment_services.send_order_notification") as mock_send:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                result=update_order_fulfillment_status(
                    self.order.pk,
                    new_status,
                )
                self.assertEqual(result,"updated")
                mock_send.assert_not_called()
            self.assertEqual(len(callbacks),1)
            mock_send.assert_called_once_with(
                self.order.pk,
                notification_type,
            )
        self.order.refresh_from_db()
        self.assertEqual(self.order.fulfillment_status,new_status)
    def test_processing_transition(self):
        self.assert_valid_transitions(
            Order.FulfillmentStatus.NOT_READY,
            Order.FulfillmentStatus.PROCESSING,
            OrderEmailNotification.NotificationType.PROCESSING,

        )

    def test_shipped_transitions(self):
        self.assert_valid_transitions(
            self.order.FulfillmentStatus.PROCESSING,
            self.order.FulfillmentStatus.SHIPPED,
            OrderEmailNotification.NotificationType.SHIPPED,
        )
    def test_out_for_delivery_transitions(self):
        self.assert_valid_transitions(
            self.order.FulfillmentStatus.SHIPPED,
            self.order.FulfillmentStatus.OUT_FOR_DELIVERY,
            OrderEmailNotification.NotificationType.OUT_FOR_DELIVERY,
        )
    def test_delivered_transitions(self):
        self.assert_valid_transitions(
            self.order.FulfillmentStatus.OUT_FOR_DELIVERY,
            self.order.FulfillmentStatus.DELIVERED,
            OrderEmailNotification.NotificationType.DELIVERED,
        )

    def  test_repeated_status_does_not_send_email_again(self): 
        self.order.fulfillment_status=(
            Order.FulfillmentStatus.PROCESSING
        )
        self.order.save(
            update_fields=["fulfillment_status"]
        )

        with patch("orders.fulfillment_services.send_order_notification") as mock_send:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                result=update_order_fulfillment_status(
                    self.order.pk,
                    Order.FulfillmentStatus.PROCESSING
                )
            self.assertEqual(result, "unchanged")
            self.assertEqual(len(callbacks), 0)
            mock_send.assert_not_called()

    def test_invalid_transition_is_rejected(self):
        with self.assertRaises(ValueError):
            update_order_fulfillment_status(
                self.order.pk,
                Order.FulfillmentStatus.SHIPPED,
            )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.fulfillment_status,
            Order.FulfillmentStatus.NOT_READY,
        )

    def test_cancelled_order_cannot_enter_fulfillment(self):
        self.order.status = Order.Status.CANCELLED
        self.order.save(update_fields=["status"])

        with self.assertRaises(ValueError):
            update_order_fulfillment_status(
                self.order.pk,
                Order.FulfillmentStatus.PROCESSING,
            )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.fulfillment_status,
            Order.FulfillmentStatus.NOT_READY
        )