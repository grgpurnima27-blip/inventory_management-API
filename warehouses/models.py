from django.db import models
from django.core.exceptions import ValidationError

from tenants.models import TenantManager


class Warehouse(models.Model):

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='warehouses',
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=100,
    )

    objects = TenantManager()

    city = models.CharField(
        max_length=100
    )

    location = models.CharField(
        max_length=255
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'],
                name='unique_tenant_warehouse_name'
            )
        ]

    def clean(self):

        errors = {}

        if len(self.name.strip()) < 3:
            errors['name'] = (
                'Warehouse name is too short.'
            )

        if len(self.city.strip()) < 2:
            errors['city'] = (
                'City is invalid.'
            )

        if len(self.location.strip()) < 3:
            errors['location'] = (
                'Location is invalid.'
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} - {self.city}'