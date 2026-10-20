import razorpay

from django.conf import settings
from decimal import Decimal
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
