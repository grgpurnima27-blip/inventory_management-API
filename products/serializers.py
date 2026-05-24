from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):

    class Meta:

        model = Product

        fields = [
            'id',
            'name',
            'sku',
            'category',
            'price',
            'created_at',
        ]

        read_only_fields = [
            'id',
            'created_at',
        ]

    def validate_name(self, value):

        if len(value.strip()) < 2:

            raise serializers.ValidationError(
                'Product name must contain at least 2 characters.'
            )

        return value

    def validate_price(self, value):

        if value <= 0:

            raise serializers.ValidationError(
                'Price must be greater than zero.'
            )

        return value

    def validate_sku(self, value):

        if len(value.strip()) < 3:

            raise serializers.ValidationError(
                'SKU must contain at least 3 characters.'
            )

        return value