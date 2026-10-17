from .models import Order,OrderItem
from rest_framework import serializers


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal=serializers.ReadOnlyField()

    class Meta:
        model=OrderItem
        fields=[
            "id",
            "product",
            "product_name",
            "price",
            "quantity",
            "subtotal"
        ]

        read_only_fields=fields


class OrderSerializer(serializers.ModelSerializer):
    items=OrderItemSerializer(read_only=True,many=True)

    class Meta:
        model=Order
        fields=[
            "id",
            "status",
            "total_amount",
            "items",
            "created_at",
            "updated_at"
        ]
        read_only_fields=fields