from django.contrib import admin

from .models import Inventory


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'product',
        'warehouse',
        'quantity'
    ]

    list_filter = [
        'warehouse'
    ]