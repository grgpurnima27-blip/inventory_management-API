from rest_framework import serializers
from .models import Product


class ProductReadSerializer(serializers.ModelSerializer):
    """Public - everyone can see including image"""

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'sku',
            'category',
            'price',
            'image',
            'created_at',
            'updated_at',
        ]


class ProductWriteSerializer(serializers.ModelSerializer):
    """Admin only - create/update with image upload"""

    image = serializers.ImageField(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Product
        fields = [
            'name',
            'sku',
            'category',
            'price',
            'image',
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

    def validate_image(self, value):
        if value:
            if value.size > 2 * 1024 * 1024:
                raise serializers.ValidationError(
                    'Image size must not exceed 2MB.'
                )
            allowed = ['image/jpeg', 'image/png', 'image/webp']
            if value.content_type not in allowed:
                raise serializers.ValidationError(
                    'Only JPEG, PNG, and WebP images are allowed.'
                )
        return value