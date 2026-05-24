from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):

        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError(
                'Product name must contain at least 3 characters.'
            )

        return value

    def validate_category(self, value):

        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                'Category name is too short.'
            )

        return value

    def validate_price(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                'Price must be greater than zero.'
            )

        return value

    def validate_sku(self, value):

        value = value.strip().upper()

        if len(value) < 3:
            raise serializers.ValidationError(
                'SKU must contain at least 3 characters.'
            )

        return value