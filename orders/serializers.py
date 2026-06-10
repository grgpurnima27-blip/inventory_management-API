from decimal import Decimal
from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_name   = serializers.CharField(source='product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    warehouse_city = serializers.CharField(source='warehouse.city', read_only=True)

    class Meta:
        model  = OrderItem
        fields = [
            'id', 'product', 'product_name',
            'warehouse', 'warehouse_name', 'warehouse_city',
            'quantity', 'unit_price',
        ]


class OrderCustomerSerializer(serializers.ModelSerializer):
    """
    Customer — can see their own order
    including status and payment_status but cannot edit them
    """
    items = OrderItemSerializer(many=True, read_only=True)
    user  = serializers.StringRelatedField(read_only=True)

    original_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    discount_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    total_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model  = Order
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
            'payment_transaction_id',
            'processed_at',
            'shipped_at',
            'completed_at',
            'cancelled_at',
            'paid_at',
            'created_at',
            'items',
        ]
        read_only_fields = [
            'id', 'status', 'payment_status',
            'original_amount', 'discount_amount', 'total_price',
            'payment_transaction_id', 'processed_at', 'shipped_at',
            'completed_at', 'cancelled_at', 'paid_at', 'created_at',
        ]


class OrderAdminSerializer(serializers.ModelSerializer):
    """
    Admin — sees everything and can
    update status and payment_status
    """
    items = OrderItemSerializer(many=True, read_only=True)
    user  = serializers.StringRelatedField(read_only=True)

    original_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    discount_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    total_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model  = Order
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
            'payment_transaction_id',
            'processed_at',
            'shipped_at',
            'completed_at',
            'cancelled_at',
            'paid_at',
            'created_at',
            'updated_at',
            'items',
        ]
        read_only_fields = [
            'id', 'original_amount', 'discount_amount', 'total_price',
            'payment_transaction_id', 'processed_at', 'shipped_at',
            'completed_at', 'cancelled_at', 'paid_at',
            'created_at', 'updated_at',
        ]

    def validate_status(self, value):
        order = self.instance
        if not order:
            return value

        valid_transitions = {
            Order.STATUS_PENDING:    [Order.STATUS_PROCESSING, Order.STATUS_CANCELLED],
            Order.STATUS_PROCESSING: [Order.STATUS_SHIPPED, Order.STATUS_CANCELLED],
            Order.STATUS_SHIPPED:    [Order.STATUS_COMPLETED],
            Order.STATUS_COMPLETED:  [],
            Order.STATUS_CANCELLED:  [],
        }

        allowed = valid_transitions.get(order.status, [])
        if value not in allowed:
            raise serializers.ValidationError(
                f'Cannot move from "{order.status}" to "{value}". '
                f'Allowed: {allowed}'
            )
        return value

    def validate_payment_status(self, value):
        order = self.instance
        if not order:
            return value
        if order.payment_status == 'paid' and value != 'paid':
            raise serializers.ValidationError(
                'Cannot change payment status from "paid".'
            )
        return value

    def update(self, instance, validated_data):
        from django.utils import timezone

        new_status         = validated_data.get('status')
        new_payment_status = validated_data.get('payment_status')

        if new_status:
            timestamp_map = {
                Order.STATUS_PROCESSING: 'processed_at',
                Order.STATUS_SHIPPED:    'shipped_at',
                Order.STATUS_COMPLETED:  'completed_at',
                Order.STATUS_CANCELLED:  'cancelled_at',
            }
            timestamp_field = timestamp_map.get(new_status)
            if timestamp_field:
                setattr(instance, timestamp_field, timezone.now())
            instance.status = new_status

        if new_payment_status:
            if new_payment_status == 'paid' and instance.payment_status != 'paid':
                instance.paid_at = timezone.now()
            instance.payment_status = new_payment_status

        instance.save()
        return instance


### Default serializer alias
OrderSerializer = OrderCustomerSerializer