from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

from products.models import Product
from warehouses.models import Warehouse
from tenants.models import TenantManager

from django.utils import timezone


class Order(models.Model):

    STATUS_PENDING    = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_SHIPPED    = 'shipped'
    STATUS_COMPLETED  = 'completed'
    STATUS_CANCELLED  = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING,    'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_SHIPPED,    'Shipped'),
        (STATUS_COMPLETED,  'Completed'),
        (STATUS_CANCELLED,  'Cancelled'),
    ]

    PAYMENT_METHOD_ESEWA  = 'esewa'
    PAYMENT_METHOD_COD    = 'cod'
    PAYMENT_METHOD_KHALTI = 'khalti'

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_ESEWA,  'eSewa'),
        (PAYMENT_METHOD_COD,    'Cash on Delivery'),
        (PAYMENT_METHOD_KHALTI, 'Khalti'),
    ]

    PAYMENT_STATUS_PENDING  = 'pending'
    PAYMENT_STATUS_PAID     = 'paid'
    PAYMENT_STATUS_FAILED   = 'failed'
    PAYMENT_STATUS_REFUNDED = 'refunded'

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PENDING,  'Pending'),
        (PAYMENT_STATUS_PAID,     'Paid'),
        (PAYMENT_STATUS_FAILED,   'Failed'),
        (PAYMENT_STATUS_REFUNDED, 'Refunded'),
    ]

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='orders',
        null=True,
        blank=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    customer_name = models.CharField(max_length=255)

    delivery_city = models.CharField(
        max_length=100,
        default='Kathmandu'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        default=PAYMENT_METHOD_COD
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_STATUS_PENDING
    )

    payment_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        help_text='eSewa or Khalti transaction ID after successful payment'
    )

    original_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    processed_at = models.DateTimeField(null=True, blank=True)
    shipped_at   = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    paid_at      = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        errors = {}
        
        if self.customer_name and len(self.customer_name.strip()) < 3:
            errors['customer_name'] = 'Customer name must contain at least 3 characters.'
        
        if self.delivery_city and len(self.delivery_city.strip()) < 2:
            errors['delivery_city'] = 'Delivery city is invalid.'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Order #{self.id} - {self.customer_name} - {self.status} - {self.payment_method}'


class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE
    )

    quantity   = models.PositiveIntegerField()
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        ordering = ['id']

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be greater than zero.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Order #{self.order.id} - {self.product.name} x {self.quantity}'


class Invoice(models.Model):
    order = models.OneToOneField(
        Order,
        related_name="invoice",
        on_delete=models.CASCADE
    )
    invoice_number = models.CharField(
        max_length=50,
        unique=True
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.invoice_number