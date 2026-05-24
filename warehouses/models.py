from django.db import models
from django.core.exceptions import ValidationError


class Warehouse(models.Model):

    name = models.CharField(
        max_length=100
    )

    location = models.CharField(
        max_length=255
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['name']

    def clean(self):

        errors = {}

        if len(self.name.strip()) < 3:
            errors['name'] = (
                'Warehouse name is too short.'
            )

        if len(self.location.strip()) < 2:
            errors['location'] = (
                'Location is invalid.'
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):

        return self.name