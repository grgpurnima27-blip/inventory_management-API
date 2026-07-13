from django.db import models


class ContactMessage(models.Model):

    first_name = models.CharField(max_length=100)

    last_name = models.CharField(max_length=100)

    email = models.EmailField()

    subject = models.CharField(max_length=255)

    message = models.TextField()

    is_resolved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

# Create your models here.
