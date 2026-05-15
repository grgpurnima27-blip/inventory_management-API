from rest_framework import serializers
from .models import Order, OrderItem
from products.models import Product
from inventory.models import Inventory

class OrderItemSerializer(serializers.ModelSerializer):
    product_name= serializers.CharField(
        source='product.name',
        read_only=True
    )
    warehouse_name=serializers.CharField(
        source="warehouse.name",
        read_only=True
    )

    class Meta:
        model= OrderItem 
        fields=[
            'id',
            'product',
            'product_name',
            'warehouse',
            'warehouse_name',
            'quantity',
            'unit_price',
        ]
        read_only_fields=[
            'id',
            'unit_price',
        ]

class OrderSerializer(serializers.ModelSerializer):
    items= OrderItemSerializer(many=True)
    class Meta:
        model=Order
        fields=[
            'id',
            'customer_name',
            'status',
            'created_at',
            'items',
        ]

        read_only_fields=[
            'id',
            'status',
            'created_at',
        ]