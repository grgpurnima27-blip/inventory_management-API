from django.db import transaction

from rest_framework import serializers

from .models import Order, OrderItem
from inventory.models import Inventory


class OrderItemSerializer(serializers.ModelSerializer):

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

        read_only_fields = [
            'id',
            'unit_price',
        ]


class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order

        fields = [
            'id',
            'customer_name',
            'status',
            'created_at',
            'items',
        ]

        read_only_fields = [
            'id',
            'status',
            'created_at',
        ]

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

                raise serializers.ValidationError(
                    f"Inventory does not exist for {product.name}"
                )

            if inventory.quantity < quantity:

                raise serializers.ValidationError(
                    f"Not enough stock for {product.name}. "
                    f"Available stock: {inventory.quantity}"
                )

            inventory.quantity -= quantity

            inventory.save()

            OrderItem.objects.create(
                order=order,
                product=product,
                warehouse=warehouse,
                quantity=quantity,
                unit_price=product.price
            )

        return order