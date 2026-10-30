from rest_framework import serializers

from ..models import Order,OrderItem

class AdminOrderItemSerializer(serializers.ModelSerializer):
    subtotal=serializers.ReadOnlyField(source="sub_total")

    class Meta:
        model=OrderItem
        fields=[
            "product_name",
            "price",
            "quantity",
            "subtotal",
        ]
class AdminOrderSerializer(serializers.ModelSerializer):
    user_email=serializers.ReadOnlyField(
        source="user.email",
        read_only=True
    )
    items=AdminOrderItemSerializer(read_only=True,many=True)
    class Meta:
        model=Order
        fields=[
            "id",
            "user_email",
            "status",
            "payment_status",
            "fullfilment_status",
            "total_amount",
            "stock_reserved",
            "requires_conncilation",
            "is_for_someone_else",
            "delivery_address_snapshot",
            "items",
            "created_at",
            "updated_at",


        ]
        read_only_fields=fields

class FulfillmentStatusUpdateSerializer(serializers.Serializer):
    fulfillment_status=serializers.ChoiceField(
        choices=[
            Order.FulfillmentStatus.PROCESSING,
            Order.FulfillmentStatus.SHIPPED,
            Order.FulfillmentStatus.OUT_FOR_DELIVERY,
            Order.FulfillmentStatus.DELIVERED
        ]

    )