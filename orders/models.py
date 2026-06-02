from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

from products.models import Product
from warehouses.models import Warehouse


class Order(models.Model):

    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'    
    STATUS_SHIPPED = 'shipped'          
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),  
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    # Payment method choices
    PAYMENT_METHOD_ESEWA = 'esewa'
    PAYMENT_METHOD_COD = 'cod'
    
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_ESEWA, 'eSewa (QR Code)'),
        (PAYMENT_METHOD_COD, 'Cash on Delivery'),
    ]

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

    # Payment method field
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        default=PAYMENT_METHOD_COD
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
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

    # Payment tracking fields (optional)
    payment_status = models.CharField(
        max_length=20,
        default='pending',
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ]
    )
    
    payment_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='eSewa transaction ID after successful payment'
    )

    # Tracking timestamps
    processed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        errors = {}
        if len(self.customer_name.strip()) < 3:
            errors['customer_name'] = (
                'Customer name must contain at least 3 characters.'
            )
        if len(self.delivery_city.strip()) < 2:
            errors['delivery_city'] = 'Delivery city is invalid.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Order #{self.id} - {self.customer_name} - {self.status}'
    
    @property
    def needs_qr_code(self):
        """Check if order needs QR code for payment"""
        return self.payment_method == self.PAYMENT_METHOD_ESEWA and self.payment_status == 'pending'


class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        ordering = ['id']

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError({
                'quantity': 'Quantity must be greater than zero.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Order #{self.order.id} - {self.product.name} x {self.quantity}'