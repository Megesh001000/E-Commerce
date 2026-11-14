from rest_framwork import serializers

from ..models import Product,StockAdjustment

class StaffInventoryProductSerializer(serializers.ModelSerializer):
    class Meta:
        model=Product
        fields=[
            "id",
            "name",
            "category",
            "brand",
            "price",
            "stock",
            "updated_at"
        ]
        read_only_fields=fields

class StockAdjustmentCreateSerializer(serializers.Serializer):
    quantity_change=serializers.IntegerField()

    reason=serializers.CharField(choices=StockAdjustment.Reason.choices)

    note=serializers.CharField(max_length=255,required=False,allow_blank=True,default="")

class StockAdjustmentHistorySerializer(serializers.ModelSerializer):

    product_name = serializers.ReadOnlyField(
        source="product.name"
    )

    adjusted_by_username = serializers.ReadOnlyField(
        source="adjusted_by.username"
    )

    class Meta:
        model = StockAdjustment
        fields = [
            "id",
            "product",
            "product_name",
            "adjusted_by",
            "adjusted_by_username",
            "quantity_change",
            "previous_stock",
            "new_stock",
            "reason",
            "note",
            "created_at",
        ]
        read_only_fields = fields