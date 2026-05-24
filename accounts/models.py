# Create your models here.

from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('customer', 'Customer'),
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='customer'
    )

    def is_admin_user(self):
        return self.role == 'admin'
