from django.db import models
from django.core.exceptions import ValidationError


class Product(models.Model):

    name = models.CharField(
        max_length=100
    )

    sku = models.CharField(
        max_length=75,
        unique=True
    )

    category = models.CharField(
        max_length=100
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

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