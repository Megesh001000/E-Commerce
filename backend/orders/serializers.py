from .models import Order,OrderItem,DeliveryAddress
from rest_framework import serializers
from django.db import transaction

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

class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model=DeliveryAddress
        fields=[
            "id",
            "label",
            "recipient_name",
            "phone",
            "address_line1",
            "address_line2",
            "locality",
            "city",
            "state",
            "postal_code",
            "country",
            "latitude",
            "longitude",
            "is_default",
            "created_at",
            "updated_at",

        ]

        read_only_fields=[
            "id",
            "created_at",
            "updated_at"
        ]
        def create(self,validated_data):
            user=self.context["request"].user
            with transaction.atomic():
                if validated_data.get("is_default",False):
                    DeliveryAddress.objects.filter(
                        user=user,
                        is_default=True,
                    ).update(is_default=False)
                return DeliveryAddress.objects.create(
                    user=user,
                    **validated_data,
                )

        def update(self,instance,validated_data):
            with transaction.atomic():
                if validated_data.get("is_default",instance.is_default,):
                    DeliveryAddress.objects.filter(
                        user=instance.user,
                        is_default=True,
                    ).exclude(pk=instance.pk).update(is_default=False)

                return super().update(instance,validated_data)
