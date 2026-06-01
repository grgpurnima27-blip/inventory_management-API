from decimal import Decimal

from django.db import transaction

from rest_framework import serializers

from inventory.models import Inventory
from coupons.models import Coupon
from warehouses.models import Warehouse

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model  = OrderItem
        fields = ['product', 'quantity']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Quantity must be greater than zero.'
            )
        return value


class OrderItemReadSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )
    warehouse_name = serializers.CharField(
        source='warehouse.name',
        read_only=True
    )
    warehouse_city = serializers.CharField(
        source='warehouse.city',
        read_only=True
    )

    class Meta:
        model  = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'warehouse',
            'warehouse_name',
            'warehouse_city',
            'quantity',
            'unit_price',
        ]


class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemReadSerializer(many=True, read_only=True)

    create_items = OrderItemSerializer(many=True, write_only=True)

    user = serializers.StringRelatedField(read_only=True)

    coupon_code = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        allow_null=True,      #  accepts null from Swagger
        default=None,         #  defaults to None if not provided
        help_text='Enter a coupon code to get a discount (optional).'
    )

    discount_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    original_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model  = Order
        fields = [
            'id',
            'user',
            'customer_name',
            'delivery_city',
            'status',
            'original_amount',
            'discount_amount',
            'total_price',
            'coupon_code',
            'created_at',
            'items',
            'create_items',
        ]
        read_only_fields = [
            'id',
            'status',
            'total_price',
            'created_at',
            'discount_amount',
            'original_amount',
        ]

    @transaction.atomic
    def create(self, validated_data):

        items_data    = validated_data.pop('create_items')
        coupon_code   = validated_data.pop('coupon_code', None)
        delivery_city = validated_data['delivery_city']
        user          = self.context['request'].user

        # Validate coupon early before touching inventory
        coupon = None
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code.upper())
            except Coupon.DoesNotExist:
                raise serializers.ValidationError({
                    'coupon_code': 'Coupon code not found.'
                })

            is_valid, message = coupon.is_valid()
            if not is_valid:
                raise serializers.ValidationError({
                    'coupon_code': message
                })

        # Create order with PENDING status
        order = Order.objects.create(
            user   = user,
            status = Order.STATUS_PENDING,   ### stays pending until admin updates
            **validated_data
        )

        total_price = Decimal('0.00')

        # Process each item — lock inventory row to prevent race conditions
        for item_data in items_data:

            product  = item_data['product']
            quantity = item_data['quantity']

            # select_for_update locks the row so concurrent requests wait
            inventory = Inventory.objects.select_for_update().filter(
                product=product,
                warehouse__city__iexact=delivery_city,
                quantity__gte=quantity
            ).first()

            if not inventory:
                raise serializers.ValidationError({
                    'stock': (
                        f'Sorry, {product.name} is out of stock in '
                        f'{delivery_city} with the requested quantity.'
                    )
                })

            inventory.quantity -= quantity
            inventory.save()

            OrderItem.objects.create(
                order      = order,
                product    = product,
                warehouse  = inventory.warehouse,
                quantity   = quantity,
                unit_price = product.price
            )

            total_price += product.price * quantity

        # Calculate discount
        total_price     = total_price.quantize(Decimal('0.01'))
        original_amount = total_price
        discount_amount = Decimal('0.00')

        if coupon:
            if total_price < coupon.minimum_order_amount:
                raise serializers.ValidationError({
                    'coupon_code': (
                        f'Minimum order amount for this coupon is '
                        f'NPR {coupon.minimum_order_amount}.'
                    )
                })

            if coupon.discount_type == Coupon.TYPE_PERCENTAGE:
                discount_amount = (coupon.discount_value / 100) * total_price
            else:
                discount_amount = Decimal(str(coupon.discount_value))

            discount_amount = discount_amount.quantize(Decimal('0.01'))
            discount_amount = min(discount_amount, total_price)
            total_price     = (total_price - discount_amount).quantize(Decimal('0.01'))

            coupon.used_count += 1
            coupon.save(update_fields=['used_count'])

        # Save final totals — status stays PENDING 
        order.total_price    = total_price
        order.original_amount = original_amount
        order.discount_amount = discount_amount
        order.save(update_fields=[
            'total_price',
            'original_amount',
            'discount_amount',
        ])

        return order