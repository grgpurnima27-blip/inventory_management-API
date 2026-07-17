from django.contrib import admin

from .models import Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'name',
        'location',
        # "latitude",
        # 'longitude',
        'created_at',
        "updated_at",
    ]

    search_fields = [
        'name',
        'location',
        'city',
        'tenant__name',
    ]

    ordering = [
        'name',
    ]
    list_per_page = 20