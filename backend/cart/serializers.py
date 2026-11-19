from .models import Cart,CartItem
from products.models import Product
from decimal import Decimal

from rest_framework import serializers

class CartItemSerializer(serializers.ModelSerializer):
    product_name=serializers.CharField(
        source="product.name",
        read_only=True
    )
    product_price=serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True

    )
    subtotal=serializers.SerializerMethodField()

    class Meta:
        model=CartItem
        fields=[
            "id",
            "product",
            "product_name",
            "product_price",
            "quantity",
            "subtotal",
            "added_at",
        ]
        read_only_fields = fields

    def get_subtotal(self,obj):
            return obj.product.price * obj.quantity

class CartSerializer(serializers.ModelSerializer):
    items=CartItemSerializer(many=True,read_only=True)
    total=serializers.SerializerMethodField()

    class Meta:
        model=Cart
        fields=[
            "id",
            "items",
            
            "total",
            "created_at",
            "updated_at"

        ]
        read_only_fields=fields

    def get_total(self,obj):
            return sum(
                (item.product.price * item.quantity  for item in obj.items.all()),
                start=Decimal("0.00")
            )
class AddCartItemSerializer(serializers.Serializer):
    product_id=serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
    )
    quantity=serializers.IntegerField(
         min_value=1,default=1,
    )
class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        min_value=1,
    )