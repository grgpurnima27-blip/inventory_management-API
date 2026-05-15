from django.db import models

# Create your models here.
class Warehouse(models.Model):
    name= models.CharField(max_length=150)
    location= models.CharField(max_length=255)


    def __str__(self):
        return self.name
 