from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

from products.models import Product


class Wishlist(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlisted_by'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_user_product_wishlist'
            )
        ]

    def __str__(self):
        return f'{self.user.username} → {self.product.name}'