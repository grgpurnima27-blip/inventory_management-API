from rest_framework import serializers
from .models import Wishlist


class WishlistReadSerializer(serializers.ModelSerializer):

    product_id = serializers.IntegerField(
        source='product.id',
        read_only=True
    )

    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )

    product_price = serializers.DecimalField(
        source='product.price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    product_image = serializers.ImageField(
        source='product.image',
        read_only=True
    )

    product_category = serializers.CharField(
        source='product.category',
        read_only=True
    )

    class Meta:
        model = Wishlist
        fields = [
            'id',
            'product_id',
            'product_name',
            'product_price',
            'product_image',
            'product_category',
            'created_at',
        ]


class WishlistWriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Wishlist
        fields = ['product']

    def validate(self, data):
        user = self.context['request'].user
        product = data['product']

        if Wishlist.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError({
                'product': 'This product is already in your wishlist.'
            })

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        return Wishlist.objects.create(
            user=user,
            **validated_data
        )