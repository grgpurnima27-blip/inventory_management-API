from django.db import models

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

    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'warehouse'],
                name='unique_product_warehouse'
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.warehouse.name}"
    