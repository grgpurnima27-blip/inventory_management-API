from rest_framework import serializers

from .models import Warehouse


class WarehouseSerializer(serializers.ModelSerializer):

    class Meta:

        model = Warehouse

        fields = [
            'id',
            'name',
            'city',
            'location',
            'latitude',
            'longitude',
            'created_at',
        ]

        read_only_fields = [
            'id',
            'created_at',
        ]

    def validate_latitude(self, value):
        if value is not None: 
            if value < -90 or value > 90:
                raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if value is not None:
            if value < -180 or value > 180:
                raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value