from django.contrib import admin

from .models import Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display=(
        "name","slug","created_at","updated_at"
    )
    search_fields=("name",)
    ordering=("name",)
    list_filter=("created_at",)
