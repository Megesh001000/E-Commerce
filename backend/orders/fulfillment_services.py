from django.db import transaction

from orders.models import Order,OrderEmailNotification
from orders.emails.email_services import send_order_notification

def update_order_fulfillment_status(order_id,new_status):
    notification_mapping={
        Order.FulfillmentStatus.PROCESSING:OrderEmailNotification.NotificationType.PROCESSING,

        Order.FulfillmentStatus.SHIPPED:OrderEmailNotification.NotificationType.SHIPPED,

        Order.FulfillmentStatus.OUT_FOR_DELIVERY:OrderEmailNotification.NotificationType.OUT_FOR_DELIVERY,

        Order.FulfillmentStatus.DELIVERED:OrderEmailNotification.NotificationType.DELIVERED
    }

    allowed_transitons={
        Order.FulfillmentStatus.NOT_READY:Order.FulfillmentStatus.PROCESSING,

        Order.FulfillmentStatus.PROCESSING:Order.FulfillmentStatus.SHIPPED,

        Order.FulfillmentStatus.SHIPPED:Order.FulfillmentStatus.OUT_FOR_DELIVERY,

        Order.FulfillmentStatus.OUT_FOR_DELIVERY:Order.FulfillmentStatus.DELIVERED,
    }

    if new_status not in notification_mapping:
        raise ValueError("Invalid fulfillment status.")

    with transaction.atomic():
        order=Order.objects.select_for_update().get(
            pk=order_id
        )
        if order.status != Order.Status.CONFIRMED:
            raise ValueError ("Only confirmed orders can be processed for delivery.")

        current_status=order.fulfillment_status

        if current_status == new_status:         # repeated updates should not send another email.

            return "unchanged"

        expected_status=allowed_transitons.get(current_status)

        if expected_status != new_status:
            raise ValueError(
                f"Invalid fulfillment transition: "
                f"{current_status} -> {new_status}"
            )
        order.fulfillment_status=new_status

        order.save(
            update_fields=[
                "fulfillment_status",
                "updated_at",
            ]
        )
        notification_type=notification_mapping[new_status]

        transaction.on_commit(
            lambda order_id=order.pk,notification_type=notification_type:
            send_order_notification(
                order_id,
                notification_type,
            ),
            robust=True

        )

    return "updated"