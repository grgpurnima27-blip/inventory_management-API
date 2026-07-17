
# orders/admin.py

from django.contrib import admin
from django.utils.html import format_html

from .models import Invoice, Order, OrderItem, OrderPrescription, Delivery
# Payment model removed - using payment app instead


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
        'payment_status',
        'total_price',
        'created_at',
    ]
    list_filter = [
        'status',
        'payment_status',
        'payment_method',
        'created_at',
    ]
    search_fields = [
        'customer_name',
        'user__username',
        'user__email',
        'payment_transaction_id',
    ]
    ordering = [
        '-created_at',
    ]
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'paid_at', 
        'processed_at', 
        'shipped_at', 
        'completed_at', 
        'cancelled_at'
    ]
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'customer_name', 'delivery_city', 'delivery_address')
        }),
        ('Order Details', {
            'fields': ('tenant', 'original_amount', 'discount_amount', 'total_price', 'delivery_charge', 'notes')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_status', 'payment_transaction_id', 'paid_at')
        }),
        ('Order Status', {
            'fields': ('status', 'processed_at', 'shipped_at', 'completed_at', 'cancelled_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
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
        'total_price_display',
    ]
    search_fields = [
        'product__name',
        'order__customer_name',
        'order__id',
    ]
    list_filter = [
        'warehouse',
        'order__status',
    ]
    
    def total_price_display(self, obj):
        return obj.total_price
    total_price_display.short_description = 'Total Price'


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "order",
        "amount",
        "total_amount",
        "status",
        "created_at",
    )
    list_filter = [
        'status',
        'created_at',
    ]
    search_fields = (
        "invoice_number",
        "order__id",
        "order__customer_name",
    )
    ordering = (
        "-created_at",
    )
    readonly_fields = ['created_at', 'issued_at', 'paid_at']
    
    fieldsets = (
        ('Invoice Details', {
            'fields': ('invoice_number', 'order', 'status')
        }),
        ('Amount Details', {
            'fields': ('amount', 'tax_amount', 'discount_amount', 'total_amount')
        }),
        ('Billing Information', {
            'fields': ('billing_address', 'pdf_file')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'issued_at', 'paid_at')
        }),
    )


@admin.register(OrderPrescription)
class OrderPrescriptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'status', 'uploaded_at', 'reviewed_at', 'reviewed_by']
    list_filter = ['status', 'uploaded_at']
    search_fields = ['order__id', 'order__user__email', 'order__customer_name']
    readonly_fields = ['uploaded_at', 'reviewed_at']
    
    fields = ['order', 'image', 'status', 'notes', 'uploaded_at', 'reviewed_by', 'reviewed_at']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return ['uploaded_at', 'reviewed_at'] + super().get_readonly_fields(request, obj)
        return super().get_readonly_fields(request, obj)


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'order', 
        'status', 
        'tracking_number', 
        'delivery_partner', 
        'estimated_delivery'
    ]
    list_filter = ['status', 'delivery_partner', 'created_at']
    search_fields = ['order__id', 'tracking_number', 'order__customer_name']
    readonly_fields = ['created_at', 'updated_at', 'delivered_at']
    
    fieldsets = (
        ('Delivery Details', {
            'fields': ('order', 'status', 'tracking_number', 'tracking_url', 'delivery_partner', 'delivery_notes')
        }),
        ('Delivery Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country', 'phone_number')
        }),
        ('Timestamps', {
            'fields': ('estimated_delivery', 'delivered_at', 'created_at', 'updated_at')
        }),
    )