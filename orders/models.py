from django.db import models
from django.core.exceptions import ValidationError

from products.models import Product
from warehouses.models import Warehouse


class Order(models.Model):

    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    customer_name = models.CharField(
        max_length=255
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

    def clean(self):

        if len(self.customer_name.strip()) < 3:

            raise ValidationError({
                'customer_name':
                'Customer name must contain at least 3 characters.'
            })

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):

        return (
            f'Order #{self.id} - '
            f'{self.customer_name}'
        )


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
                'quantity':
                'Quantity must be greater than zero.'
            })

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):

        return (
            f'Order #{self.order.id} - '
            f'{self.product.name}'
        )