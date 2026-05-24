from django.db import transaction

from rest_framework import serializers

from .models import Order
from .models import OrderItem

from inventory.models import Inventory


class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem
        fields = [
            'product',
            'warehouse',
            'quantity'
        ]

    def validate_quantity(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                'Quantity must be greater than zero.'
            )

        return value


class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'customer_name',
            'status',
            'created_at',
            'items'
        ]

        read_only_fields = [
            'id',
            'status',
            'created_at'
        ]

    def validate_customer_name(self, value):

        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError(
                'Customer name must contain at least 3 characters.'
            )

        return value

    @transaction.atomic
    def create(self, validated_data):

        items_data = validated_data.pop('items')

        order = Order.objects.create(**validated_data)

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
                    f'No inventory found for {product.name} in selected warehouse.'
                })

            if inventory.quantity < quantity:

                raise serializers.ValidationError({
                    'stock':
                    f'Insufficient stock for {product.name}. Available stock is {inventory.quantity}.'
                })

            inventory.quantity -= quantity

            inventory.save()

            OrderItem.objects.create(
                order=order,
                product=product,
                warehouse=warehouse,
                quantity=quantity,
                unit_price=product.price
            )

        order.status = Order.STATUS_COMPLETED

        order.save()

        return order