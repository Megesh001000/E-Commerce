from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core  import mail
from django.test import TestCase,override_settings

from .email_services import send_order_notification
from ..models import Order,OrderEmailNotification

User=get_user_model()
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Store <orders@example.com>",
)
class OrderEmailServiceTest(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(
            username="email_test_user",
            email="customer@example.com",
            password="test-password",
        )
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("125.00"),
            status=Order.Status.CONFIRMED,
            payment_status="captured",
            stock_reserved=False,
            delivery_address_snapshot={
                "recipient_name": "Megesh",
                "phone": "9876543210",
                "address_line1": "10 Main Street",
                "address_line2": "",
                "locality": "Guindy",
                "city": "Chennai",
                "state": "Tamil Nadu",
                "postal_code": "600045",
                "country": "India",
                "latitude": "12.924900",
                "longitude": "80.100000",
            },
        )
    def test_confirmation_email_is_sent_and_recorded(self):
        result=send_order_notification(
          self.order.pk,
          OrderEmailNotification.NotificationType.ORDER_CONFIRMED
        )
        self.assertEqual(result,"sent")
        self.assertEqual(len(mail.outbox),1)


        message=mail.outbox[0]

        self.assertEqual(
            message.subject,
            "Your order has been confirmed"
        )
        self.assertEqual(
            message.to,
            ["customer@example.com"],
        )
        self.assertIn(str(self.order.pk), message.body)
        self.assertIn("10 Main Street", message.body)
        self.assertEqual(len(message.alternatives), 1)
        self.assertEqual(
            message.alternatives[0][1],
            "text/html",
        )
        notification=OrderEmailNotification.objects.get(
            order=self.order,
            notification_type=(
                OrderEmailNotification.NotificationType.ORDER_CONFIRMED
            )
        )
        self.assertEqual(
            notification.status,
            OrderEmailNotification.Status.SENT,
        )
        self.assertEqual(notification.attempts, 1)
        self.assertIsNotNone(notification.sent_at)
    def test_duplicate_notification_is_not_sent_again(self):
        notification_type=OrderEmailNotification.NotificationType.ORDER_CONFIRMED
        first_result=send_order_notification(
            self.order.pk,
            notification_type
        )
        second_result=send_order_notification(
            self.order.pk,
            notification_type
        )
        self.assertEqual(first_result, "sent")
        self.assertEqual(second_result, "already_sent")
        self.assertEqual(len(mail.outbox), 1)

    def test_missing_customer_email_is_skipped(self):
        self.user.email=""
        self.user.save(update_fields=["email"])
        result = send_order_notification(
            self.order.pk,
            OrderEmailNotification.NotificationType.ORDER_CONFIRMED,
        )

        self.assertEqual(result, "skipped_no_email")
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(
            OrderEmailNotification.objects.filter(
                order=self.order,
            ).exists()
        )
    def test_smtp_failure_is_recorded(self):
        with patch(
            "orders.emails.email_services.EmailMultiAlternatives.send",
            side_effect=ConnectionError("SMTP unavailable"),
        ):
            with self.assertLogs(
                "orders.emails.email_services",
                level="ERROR",
            ):
                result = send_order_notification(
                    self.order.pk,
                    OrderEmailNotification.NotificationType.ORDER_CONFIRMED,
                )

        self.assertEqual(result, "failed")
        self.assertEqual(len(mail.outbox), 0)

        notification = OrderEmailNotification.objects.get(
            order=self.order,
            notification_type=(
                OrderEmailNotification.NotificationType.ORDER_CONFIRMED
            ),
        )

        self.assertEqual(
            notification.status,
            OrderEmailNotification.Status.FAILED,
        )
        self.assertEqual(notification.attempts, 1)
        self.assertIn("SMTP unavailable", notification.last_error)

    def test_unsupported_notification_type_is_rejected(self):
        with self.assertRaises(ValueError):
            send_order_notification(
                self.order.pk,
                "unsupported_type",
            )

        self.assertEqual(len(mail.outbox), 0)
