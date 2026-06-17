from rest_framework import serializers
from .models import Review


class ReviewReadSerializer(serializers.ModelSerializer):

    username = serializers.CharField(
        source='user.username',
        read_only=True
    )

    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )

    class Meta:
        model = Review
        fields = [
            'id',
            'username',
            'product',
            'product_name',
            'rating',
            'comment',
            'created_at',
            'updated_at',
        ]


class ReviewWriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Review
        fields = [
            'product',
            'rating',
            'comment',
        ]

    def validate_rating(self, value):
        if value not in range(1, 6):
            raise serializers.ValidationError(
                'Rating must be between 1 and 5.'
            )
        return value

    def validate(self, data):
        request = self.context['request']
        user = request.user
        product = data['product']
        tenant = getattr(request, 'tenant', None)

        if tenant and product.tenant_id != tenant.id:
            raise serializers.ValidationError({
                'product': 'This product does not belong to the current store.'
            })

        # Check if user already reviewed this product (on create only)
        if self.instance is None:
            if Review.objects.filter(user=user, product=product).exists():
                raise serializers.ValidationError({
                    'product': 'You have already reviewed this product.'
                })

        # Only allow review if user has purchased the product from this tenant
        from orders.models import Order, OrderItem
        qs = OrderItem.objects.filter(
            order__user=user,
            order__status=Order.STATUS_COMPLETED,
            product=product
        )
        if tenant:
            qs = qs.filter(order__tenant=tenant)
        if not qs.exists():
            raise serializers.ValidationError({
                'product': 'You can only review products you have purchased.'
            })

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        return Review.objects.create(
            user=user,
            **validated_data
        )
        

    