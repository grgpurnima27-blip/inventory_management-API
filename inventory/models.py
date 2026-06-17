from django.db import models
from django.core.exceptions import ValidationError

from products.models import Product
from warehouses.models import Warehouse
from tenants.models import TenantManager


class Inventory(models.Model):

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='inventories',
        null=True,
        blank=True,
    )

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

    updated_at = models.DateTimeField(
        auto_now=True
    )

    objects = TenantManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'product', 'warehouse'],
                name='unique_tenant_product_warehouse'
            )
        ]
        ordering = ['-updated_at']

    def clean(self):
        if self.quantity < 0:
            raise ValidationError({
                'quantity': 'Quantity cannot be negative.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f'{self.product.name} - '
            f'{self.warehouse.name}'
        )
