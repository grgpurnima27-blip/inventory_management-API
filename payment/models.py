from django.db import models
from django.conf import settings

from orders.models import Order
from tenants.models import Tenant


class Payment(models.Model):
    """
    Stores the complete payment details for an order.
    One order can have only one successful payment.
    """

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    METHOD_ESEWA = "esewa"
    METHOD_KHALTI = "khalti"
    METHOD_COD = "cod"

    METHOD_CHOICES = [
        (METHOD_ESEWA, "eSewa"),
        (METHOD_KHALTI, "Khalti"),
        (METHOD_COD, "Cash On Delivery"),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment",
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
    )

    transaction_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
    )

    gateway_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    gateway_response = models.JSONField(
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    paid_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment #{self.id} - Order #{self.order.id}"
    


class PaymentLog(models.Model):
    """
    Stores every payment event for debugging and auditing.
    """

    EVENT_INITIATED = "initiated"
    EVENT_SUCCESS = "success"
    EVENT_FAILED = "failed"
    EVENT_REFUND = "refund"
    EVENT_WEBHOOK = "webhook"

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="logs",
    )

    event = models.CharField(
        max_length=100,
    )

    response = models.JSONField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.payment.order.id} - {self.event}"
    

class Payout(models.Model):
    """
    Stores vendor payout information after a successful payment.
    """

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
    ]

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="payouts",
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payouts",
    )

    gross_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    commission = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    paid_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tenant.name} - Order #{self.order.id}"