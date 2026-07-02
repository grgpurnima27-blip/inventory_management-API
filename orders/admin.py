from django.contrib import admin

from .models import Invoice, Order, OrderItem


class OrderItemInline(admin.TabularInline):

    model = OrderItem

    extra = 0

    readonly_fields = [
        'product',
        'warehouse',
        'quantity',
        'unit_price',
    ]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'customer_name',
        'user',
        'status',
        'total_price',
        'created_at',
    ]

    list_filter = [
        'status',
        'created_at',
    ]

    search_fields = [
        'customer_name',
        'user__username',
    ]

    ordering = [
        '-created_at',
    ]

    inlines = [
        OrderItemInline,
    ]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'order',
        'product',
        'warehouse',
        'quantity',
        'unit_price',
    ]

    search_fields = [
        'product__name',
        'order__customer_name',
    ]

    list_filter = [
        'warehouse',
    ]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):

    list_display = (
        "invoice_number",
        "order",
        "generated_at"
    )

    search_fields = (
        "invoice_number",
    )

    ordering = (
        "-generated_at",
    )