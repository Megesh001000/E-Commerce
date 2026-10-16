from rest_framework import serializers
from .models import Brand, Product,Tag,ProductImage
from categories.models import Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model=Category
        fields=[
            "id",
            "name",
            "slug"
        ]
class BrandSerializer(serializers.ModelSerializer):
    class  Meta:
        model=Brand
        fields=[
            "id",
            "name",
            "slug",
        ]
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model=Tag
        fields=[
            "id",
            "name",
            "slug",
        ]
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model=ProductImage
        fields=[
            "id",
            "image",
            "image_url",
            "is_primary",
            "created_at",
            "updated_at",
        ]


class ProductSerializer(serializers.ModelSerializer):
    brand=BrandSerializer(read_only=True)
    tags=TagSerializer(read_only=True,many=True)
    category=CategorySerializer(read_only=True)
    images=ProductImageSerializer(read_only=True,many=True)

    category_id=serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True
    )

    brand_id=serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(),
        source="brand",
        write_only=True,
        required=False,
        allow_null=True,

    )

    tag_ids=serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        source="tags",
        write_only=True,
        required=False,
        many=True,
    )
    class Meta:
        model=Product
        fields=[
            "id",
            "name",
            "category",
            "category_id",
            "brand",
            "brand_id",
            "tags",
            "tag_ids",
            "images",
            "description",
            
            "price",
            "stock",
            "slug",
            "created_at",
            "updated_at",
        ]
        read_only_fields=[
             "id",
            "slug",
            "created_at",
            "updated_at",
        ]
