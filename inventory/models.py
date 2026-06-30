from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.conf import settings

from products.models import Product
from warehouses.models import Warehouse
from tenants.models import TenantManager


class Inventory(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="inventories",
        null=True,
        blank=True,
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="inventories",
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="inventories",
    )

    quantity = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "product", "warehouse"],
                name="unique_tenant_product_warehouse",
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.warehouse.name}"


class InventoryTransaction(models.Model):
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    RETURN = "RETURN"
    DAMAGE = "DAMAGE"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER = "TRANSFER"

    TRANSACTION_TYPES = [
        (PURCHASE, "Purchase"),
        (SALE, "Sale"),
        (RETURN, "Return"),
        (DAMAGE, "Damage"),
        (ADJUSTMENT, "Adjustment"),
        (TRANSFER, "Transfer"),
    ]

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="inventory_transactions",
    )

    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
    )

    quantity = models.PositiveIntegerField()

    remarks = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_transactions",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type} - {self.inventory.product.name}"

    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self.pk is None

        super().save(*args, **kwargs)

        if not is_new:
            return

        inventory = self.inventory

        if self.transaction_type in [self.PURCHASE, self.RETURN, self.ADJUSTMENT]:
            inventory.quantity += self.quantity

        elif self.transaction_type in [self.SALE, self.DAMAGE]:
            if inventory.quantity < self.quantity:
                raise ValidationError("Insufficient stock.")
            inventory.quantity -= self.quantity

        inventory.save(update_fields=["quantity"])