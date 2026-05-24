from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'name',
        'sku',
        'category',
        'price',
        'created_at',
    ]

    search_fields = [
        'name',
        'sku',
        'category',
    ]

    list_filter = [
        'category',
        'created_at',
    ]

    ordering = [
        '-created_at',
    ]