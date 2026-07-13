from rest_framework import serializers

from .models import ContactMessage


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "subject",
            "message",
            "is_resolved",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "is_resolved",
            "created_at",
        ]