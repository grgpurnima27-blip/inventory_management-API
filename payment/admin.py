from django.contrib import admin

from .models import Payment, PaymentLog, Payout


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "customer",
        "payment_method",
        "amount",
        "status",
        "transaction_id",
        "paid_at",
    )

    list_filter = (
        "status",
        "payment_method",
    )

    search_fields = (
        "transaction_id",
        "customer__email",
        "order__id",
    )

    readonly_fields = (
        "gateway_response",
        "paid_at",
        "created_at",
        "updated_at",
    )


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "payment",
        "event",
        "created_at",
    )

    list_filter = (
        "event",
    )

    readonly_fields = (
        "response",
        "created_at",
    )


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "tenant",
        "order",
        "gross_amount",
        "commission",
        "net_amount",
        "status",
    )

    list_filter = (
        "status",
    )

    readonly_fields = (
        "created_at",
        "paid_at",
    )