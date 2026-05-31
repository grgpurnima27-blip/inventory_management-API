from django.db import models

# Create your models here.
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Coupon(models.Model):

    TYPE_PERCENTAGE = 'percentage'
    TYPE_FIXED = 'fixed'

    TYPE_CHOICES = [
        (TYPE_PERCENTAGE, 'Percentage'),
        (TYPE_FIXED, 'Fixed Amount'),
    ]

    code = models.CharField(
        max_length=50,
        unique=True
    )

    discount_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_PERCENTAGE
    )

    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    max_uses = models.PositiveIntegerField(
        default=1
    )

    used_count = models.PositiveIntegerField(
        default=0
    )

    is_active = models.BooleanField(
        default=True
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        errors = {}

        if self.discount_value <= 0:
            errors['discount_value'] = (
                'Discount value must be greater than zero.'
            )

        if self.discount_type == self.TYPE_PERCENTAGE:
            if self.discount_value > 100:
                errors['discount_value'] = (
                    'Percentage discount cannot exceed 100%.'
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.code = self.code.upper()   # always uppercase
        self.full_clean()
        super().save(*args, **kwargs)

    def is_valid(self):
        if not self.is_active:
            return False, 'Coupon is inactive.'
        if self.used_count >= self.max_uses:
            return False, 'Coupon has reached its maximum uses.'
        if self.expires_at and timezone.now() > self.expires_at:
            return False, 'Coupon has expired.'
        return True, 'Valid'

    def __str__(self):
        return f'{self.code} - {self.discount_type} - {self.discount_value}'