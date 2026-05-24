from decimal import Decimal

from django.db import transaction

from rest_framework import serializers

from inventory.models import Inventory

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:

        model = OrderItem

        fields = [
            'product',
            'warehouse',
            'quantity',
        ]

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

    class Meta:

        model = OrderItem

        fields = [
            'id',
            'product',
            'product_name',
            'warehouse',
            'warehouse_name',
            'quantity',
            'unit_price',
        ]


class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemReadSerializer(
        many=True,
        read_only=True
    )

    create_items = OrderItemSerializer(
        many=True,
        write_only=True
    )

    user = serializers.StringRelatedField(
        read_only=True
    )

    class Meta:

        model = Order

        fields = [
            'id',
            'user',
            'customer_name',
            'status',
            'total_price',
            'created_at',
            'items',
            'create_items',
        ]

        read_only_fields = [
            'id',
            'status',
            'total_price',
            'created_at',
        ]

    def validate_customer_name(self, value):

        if len(value.strip()) < 3:

            raise serializers.ValidationError(
                'Customer name must contain at least 3 characters.'
            )

        return value

    @transaction.atomic
    def create(self, validated_data):

        items_data = validated_data.pop('create_items')

        user = self.context['request'].user

        order = Order.objects.create(
            user=user,
            **validated_data
        )

        total_price = Decimal('0.00')

        for item_data in items_data:

            product = item_data['product']
            warehouse = item_data['warehouse']
            quantity = item_data['quantity']

            try:

                inventory = Inventory.objects.select_for_update().get(
                    product=product,
                    warehouse=warehouse
                )

            except Inventory.DoesNotExist:

                raise serializers.ValidationError({
                    'inventory':
                    f'{product.name} does not exist in {warehouse.name}.'
                })

            if inventory.quantity < quantity:

                raise serializers.ValidationError({
                    'stock':
                    (
                        f'Only {inventory.quantity} items available '
                        f'for {product.name} in {warehouse.name}.'
                    )
                })

            inventory.quantity -= quantity
            inventory.save()

            unit_price = product.price

            OrderItem.objects.create(
                order=order,
                product=product,
                warehouse=warehouse,
                quantity=quantity,
                unit_price=unit_price
            )

            total_price += unit_price * quantity

        order.total_price = total_price
        order.status = Order.STATUS_COMPLETED
        order.save()

        return order