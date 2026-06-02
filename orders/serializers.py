from rest_framework import serializers
from .models import Order, OrderItem
from products.models import Product
from warehouses.models import Warehouse


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    warehouse_city = serializers.CharField(source='warehouse.city', read_only=True)

    class Meta:
        model = OrderItem
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
    items = OrderItemSerializer(many=True, read_only=True)
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'customer_name',
            'delivery_city',
            'status',
            'payment_method',
            'payment_status',
            'original_amount',
            'discount_amount',
            'total_price',
            'created_at',
            'items',
        ]
        read_only_fields = ['status', 'payment_status', 'created_at']