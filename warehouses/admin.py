from django.contrib import admin

from .models import Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'name',
        'location',
    ]

    search_fields = [
        'name',
        'location',
    ]

    ordering = [
        'name',
    ]