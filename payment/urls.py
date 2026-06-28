from django.urls import path

from .views import (
    PaymentHistoryView,
    PaymentDetailView,
    RefundPaymentView,
    PaymentLogListView,
    PayoutListView,
)

from .webhooks import (
    KhaltiWebhookView,
    EsewaWebhookView,
)

urlpatterns = [

    path(
        "",
        PaymentHistoryView.as_view(),
        name="payment-history",
    ),

    path(
        "<int:pk>/",
        PaymentDetailView.as_view(),
        name="payment-detail",
    ),

    path(
        "<int:pk>/refund/",
        RefundPaymentView.as_view(),
        name="payment-refund",
    ),

    path(
        "logs/",
        PaymentLogListView.as_view(),
        name="payment-logs",
    ),

    path(
        "payouts/",
        PayoutListView.as_view(),
        name="payouts",
    ),

    path(
        "webhook/khalti/",
        KhaltiWebhookView.as_view(),
        name="khalti-webhook",
    ),

    path(
        "webhook/esewa/",
        EsewaWebhookView.as_view(),
        name="esewa-webhook",
    ),
]