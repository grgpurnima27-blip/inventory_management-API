from django.db import models
from django.core.exceptions import ValidationError

from products.models import Product
from warehouses.models import Warehouse


class Inventory(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='inventories'
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='inventories'
    )

    quantity = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    constraints = [
    models.UniqueConstraint(
        fields=['product', 'warehouse'],
        name='unique_product_warehouse'
    )
]


    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=['product', 'warehouse'],
                name='unique_product_warehouse'
            )
        ]

        ordering = ['product__name']

    def clean(self):

        if self.quantity < 0:

            raise ValidationError({
                'quantity':
                'Quantity cannot be negative.'
            })

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):

        return (
            f'{self.product.name} - '
            f'{self.warehouse.name}'
        )
