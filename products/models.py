from django.db import models
from django.core.exceptions import ValidationError
from cloudinary.models import CloudinaryField

from tenants.models import TenantManager


class Product(models.Model):

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=100
    )

    sku = models.CharField(
        max_length=75,
    )

    objects = TenantManager()

    category = models.CharField(
        max_length=100
    )

    quantity = models.PositiveIntegerField(default=0)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    image = CloudinaryField(
        'image',
        null=True,
        blank=True,
        folder='products/',
    )
    requires_prescription = models.BooleanField(default=False)
    
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
                fields=['tenant', 'sku'],
                name='unique_tenant_sku'
            )
        ]

    def clean(self):
        errors = {}

        if len(self.name.strip()) < 3:
            errors['name'] = (
                'Product name must contain at least 3 characters.'
            )

        if len(self.category.strip()) < 2:
            errors['category'] = (
                'Category name is too short.'
            )

        if self.price <= 0:
            errors['price'] = (
                'Price must be greater than zero.'
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.sku})'