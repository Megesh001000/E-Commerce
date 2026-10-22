import razorpay

from decimal import Decimal

from django.conf import settings
from django.db import transaction,IntegrityError

from .models import Order



def  get_razorpay_client():
    return razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET,
            )
    )

def create_razorpay_order(order):
    client=get_razorpay_client()

    amount_in_paise=int(order.total_amount * Decimal("100"))

    razorpay_order=client.order.create(
        data={
            "amount":amount_in_paise,
            "currency":"INR",
            "receipt":str(order.id),

        }
    )

    order.razorpay_order_id=razorpay_order["id"]

    order.save(update_fields=["razorpay_order_id","updated_at"])

    return razorpay_order
def confirm_captured_payment(order,payment_id):
    if (
        order.payment_status=="captured" and  order.razorpay_payment_id==payment_id
    ):
        return "already_processed"
    # if Order.objects.filter(razorpay_payment_id=payment_id).exclude(id=order.id).exists():
    #     order.required_reconciliation=True
    #     order.save(update_fields=["requires_reconciliation","updated_at",])
    #     raise ValueError("Payment ID is already assigned to another order.")
        
    payment_exists = Order.objects.filter(
        razorpay_payment_id=payment_id
    ).exclude(id=order.id).exists()

    if payment_exists:
        return "payment_conflict"

    if order.status==Order.Status.CANCELLED:
        order.razorpay_payment_id=payment_id
        order.payment_status="captured"
        order.requires_reconciliation=True
        order.save(
            update_fields=[
                "razorpay_payment_id",
                "payment_status",
                "requires_reconciliation",
                "updated_at",
            ]
        )
        return "reconciliation_required"
    if (
        order.status != Order.Status.PENDING
        or not order.stock_reserved
        or order.payment_status != "pending"
    ):
        raise ValueError("Order state is incompatible with payment confirmation.")

    order.razorpay_payment_id=payment_id
    order.payment_status="captured"
    order.status=Order.Status.CONFIRMED
    order.requires_reconciliation=False
    order.stock_reserved = False
    
    order.save(
        update_fields=[
            "razorpay_payment_id",
            "payment_status",
            "status",
            "stock_reserved",
             "requires_reconciliation",
            "updated_at",
        ]
    )
    return "confirmed"


def process_captured_payment(event_data):
    try:                # Extract the payment details from Razorpay's webhook payload.
        payment=event_data["payload"]["payment"]["entity"]
        payment_id=payment["id"]
        razorpay_order_id=payment["order_id"]
        amount=payment["amount"]
        currency=payment["currency"]
        payment_status=payment["status"]
    except (KeyError,TypeError):
        raise ValueError("Invalid payment event payload.")

    if payment_status !="captured":  # Only process genuinely captured payments.
        raise ValueError("Payment has not been captured.")
    if (
        not isinstance(payment_id, str)
        or not payment_id
        or not isinstance(razorpay_order_id, str)
        or not razorpay_order_id
        or isinstance(amount, bool)
        or not isinstance(amount, int)
        or amount <= 0
        or not isinstance(currency, str)
    ):
        raise ValueError("Invalid payment details.")

    with transaction.atomic():
        try:
            order=Order.objects.select_for_update().get(
                razorpay_order_id=razorpay_order_id
            )
        except Order.DoesNotExist:
            raise ValueError("No matching local order was found.")

        expected_amount=int(
            order.total_amount * Decimal("100")
        )

        if amount != expected_amount  or currency != "INR":
            raise ValueError("Payment amount or currency does not match.")
        try:
            with transaction.atomic():
                return confirm_captured_payment(order,payment_id)
        except IntegrityError:
            return "payment_conflict"