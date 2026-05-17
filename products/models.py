from django.db import models
from django.core.exceptions import ValidationError

# Create your models here.

class Product(models.Model):
    name= models.CharField(max_length=100)
    sku= models.CharField(max_length=75, unique=True)
    category= models.CharField(max_length=100)
    price= models.DecimalField(max_digits=10, decimal_places=2)
    created_at=models.DateTimeField(auto_now_add=True)


    def clean(self):

        if self.price <= 0:

            raise ValidationError(
            "Price must be greater than zero"
        )
    def __str__(self):
        return self.name 