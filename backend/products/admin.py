from django.contrib import admin

from .models import Tag,Product

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display=("name","slug","created_at","updated_at")

    search_fields=("name")

    ordering=("name")

    list_filter=("created_at")

@admin.register(Product)

class ProductAdmin(admin.ModelAdmin):

    list_display=("name","category","price","stock","slug","created_at","updated_at")

    search_fields=("name","slug")

    ordering=("name")

    list_filter=("category","created_at")