import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from ..models import Order,OrderEmailNotification

logger=logging.getLogger(__name__)

NOTIFICATION_DETAILS={
    OrderEmailNotification.NotificationType.ORDER_CONFIRMED:{
        "subject":"Your order has been confirmed",
        "heading":"Order confirmed!",
        "message":"Thank you for your order. We are preparing it.",

    },
    OrderEmailNotification.NotificationType.ORDER_CANCELLED:{
        "subject":"Your order has been cancelled",
        "heading":"Order cancelled",
        "message":"Your order has been cancelled.",

    },
    OrderEmailNotification.NotificationType.PROCESSING:{
        "subject":"We are preparing your order",
        "heading":"Order proceesing",
        "message":"We are preparing you items for dispatch.",
    },
    OrderEmailNotification.NotificationType.SHIPPED:{
        "subject":"Your order has been shipped",
        "heading":"Order shipped!",
        "message":"Your order has been dispatched.",
    },
    OrderEmailNotification.NotificationType.OUT_FOR_DELIVERY:{
        "subject":"Your order is out for delivery",
        "heading":"Out for delivery ",
        "message":"your order is on it's way to your delivery address.",
    },
    OrderEmailNotification.NotificationType.DELIVERED:{
        "subject":"Your order has been delivered",
        "heading":"Delivery ",
        "message":"your order has been marked as delivered. Thank you for shopping with us.",
    },
}

def send_order_notification(order_id,notification_type):

    if notification_type not in NOTIFICATION_DETAILS:
        raise ValueError(
                    f"Unsupported order notification type: {notification_type}"
                )
    now=timezone.now()

    with transaction.atomic():
        order=Order.objects.select_related("user").get(pk=order_id)

        recipient=(order.user.email or "").strip()

        if not recipient:
            logger.warning(
                "Skipping order notification because the user has no email. "
                "Order ID: %s",
                order.pk,
            )
            return "skipped_no_email"

        notification,_=OrderEmailNotification.objects.get_or_create(
            order=order,
            notification_type=notification_type,
            defaults={"recipient_email":recipient}
        )
        notification=(
            OrderEmailNotification.objects.select_for_update().get(pk=notification.pk)
        )
        if notification.status==OrderEmailNotification.Status.SENT:
            return "already_sent"

        if notification.status==OrderEmailNotification.Status.SENDING:
            stale_before=now - timedelta(minutes=10)

            if notification.updated_at >=stale_before:
                return "already_sending"

        notification.recipient_email=recipient
        notification.status=OrderEmailNotification.Status.SENDING
        notification.attempts+=1
        notification.last_error=""
        notification.save(
            update_fields=[
                "recipient_email",
                "status",
                "attempts",
                "last_error",
                "updated_at",
            ]
        )
    details=NOTIFICATION_DETAILS[notification_type]
    try:
        items=list(order.items.all())
        delivery_address=order.delivery_address_snapshot or {}

        context = {
            "order":order,
            "items":items,
            "delivery_address":delivery_address,
            "heading":details["heading"],
            "message":details["message"],
        }


        text_body=render_to_string(
            "orders/emails/order_notification.txt",
            context,
        )

        html_body=render_to_string(
            "orders/emails/order_notification.html",
            context,
        )
        email=EmailMultiAlternatives(
            subject=details["subject"],
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        email.attach_alternative(html_body,"text/html")
        sent_count = email.send(fail_silently=False)

        if sent_count != 1:
            raise RuntimeError(
                "The email backend did not confirm sending the message."
            )

    except Exception as exc:
        logger.exception(
            "Order notification sending failed. Order ID: %s, type: %s",
            order.pk,
            notification_type,

        )
        OrderEmailNotification.objects.filter(
            pk=notification.pk,
            status=OrderEmailNotification.Status.SENDING,
        ).update(
            status=OrderEmailNotification.Status.FAILED,
            last_error=f"{type(exc).__name__}: {exc}"[:4000],
            updated_at=timezone.now()
        )
        return "failed"
    OrderEmailNotification.objects.filter(
        pk=notification.pk,
        status=OrderEmailNotification.Status.SENDING,
    ).update(
        status=OrderEmailNotification.Status.SENT,
        sent_at=timezone.now(),
        last_error="",
        updated_at=timezone.now()

    )
    return "sent"