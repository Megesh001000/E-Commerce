from django.contrib import admin

from .models import Tag,Product,ProductImage,Brand

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display=("name","slug","created_at","updated_at")

    search_fields=("name",)

    ordering=("name",)

    list_filter=("created_at",)

@admin.register(Product)

class ProductAdmin(admin.ModelAdmin):

    list_display=("name","category","price","stock","slug","created_at","updated_at")

    search_fields=("name","slug")

    ordering=("name",)

    list_filter=("category","created_at")


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display=(
        "product",
        "image",
        "image_url",
        "is_primary",
        "created_at",
        "updated_at",
    )
    list_filter=(
        "is_primary",
        "product",
        
        "created_at",
    )
    search_fields=(
        "image_url",
        "product__name",
    )

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display=(
        "name",
        "slug",
        "created_at",
        "modified_at",
    )
    search_fields=("name",)
    ordering=("name",)
    list_filter=("created_at",)


