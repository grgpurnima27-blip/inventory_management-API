from django.db import models
from django.conf import settings
from tenants.models import TenantManager


class Notification(models.Model):

    NOTIFICATION_TYPES = [
        ('order_placed',    'Order Placed'),
        ('order_processing','Order Processing'),
        ('order_shipped',   'Order Shipped'),
        ('order_completed', 'Order Completed'),
        ('order_cancelled', 'Order Cancelled'),
    ]

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
    )

    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type        = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title       = models.CharField(max_length=255)
    message     = models.TextField()
    is_read     = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.title}"