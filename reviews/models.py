from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from products.models import Product

from tenants.models import TenantManager


class Review(models.Model):

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True,
    )

    objects = TenantManager()

    RATING_CHOICES=[
        (1, '1 - Very Bad'),
        (2, '2 - Bad'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent')
    ]

    
    user= models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    product= models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='reviews'
    )

    rating= models.PositiveSmallIntegerField(choices=RATING_CHOICES)

    comment= models.TextField(null=True, blank=True)
    created_at= models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)


    class Meta:
        # one review per user per product 
        ordering= ['-created_at']
        constraints=[
            models.UniqueConstraint(fields=['user', 'product'], name='unique_user_product_review')
        ]

    def clean(self):
        if self.rating not in range(1,6):
            raise ValidationError({
                'raating' : 'Rating must be between 1 and 5.'
            })
        
    def save(self,*args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username}-{self.product}- {self.rating}'