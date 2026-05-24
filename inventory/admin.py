from django.contrib import admin

from .models import Inventory


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'product',
        'warehouse',
        'quantity',
        'stock_status',
    ]

    search_fields = [
        'product__name',
        'warehouse__name',
    ]

    list_filter = [
        'warehouse',
    ]

    ordering = [
        'quantity',
    ]

    readonly_fields = [
        'stock_status',
    ]

    def stock_status(self, obj):

        if obj.quantity == 0:
            return 'Out of Stock'

        if obj.quantity < 5:
            return 'Low Stock'

        return 'In Stock'

    stock_status.short_description = 'Stock Status'