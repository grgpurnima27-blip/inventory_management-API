from decimal import Decimal
from rest_framework import serializers
from .models import Invoice, Order, OrderItem
from inventory.services.warehouse_allocator import allocate_warehouse

from django.db import transaction
from products.models import Product
from .models import Invoice
import uuid


class OrderItemSerializer(serializers.ModelSerializer):

    product_name   = serializers.CharField(source='product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    warehouse_city = serializers.CharField(source='warehouse.city', read_only=True)

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


class OrderCustomerSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user  = serializers.StringRelatedField(read_only=True)

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
            'id',
            'user',
            'status',
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
        ]


class OrderAdminSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user  = serializers.StringRelatedField(read_only=True)

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
            'id',
            'user',
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
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"


class OrderCreateItemSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating orders with COD, eSewa, and Khalti payment methods.
    """
    customer_name = serializers.CharField()
    delivery_city = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        default=Order.PAYMENT_METHOD_COD
    )
    items = OrderCreateItemSerializer(many=True)

    def validate(self, data):
        request = self.context.get("request")
        
        # Handle delivery city
        delivery_city = data.get("delivery_city", "").strip()
        if not delivery_city and request:
            try:
                if hasattr(request.user, 'profile') and hasattr(request.user.profile, 'city'):
                    delivery_city = request.user.profile.city or ""
            except Exception:
                delivery_city = ""
        
        data['delivery_city'] = delivery_city
        
        return data

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("items")

        request = self.context["request"]
        tenant = request.tenant
        user = request.user

        order = Order.objects.create(
            tenant=tenant,
            user=user,
            customer_name=validated_data["customer_name"],
            delivery_city=validated_data.get("delivery_city", "Kathmandu"),
            payment_method=validated_data.get("payment_method", Order.PAYMENT_METHOD_COD),
            original_amount=Decimal("0.00"),
            total_price=Decimal("0.00"),
            status=Order.STATUS_PENDING,
            payment_status=Order.PAYMENT_STATUS_PENDING,
        )

        total_price = Decimal("0.00")

        for item in items:
            product = Product.objects.get(
                id=item["product"],
                tenant=tenant,
            )

            quantity = item["quantity"]
            subtotal = product.price * quantity
            total_price += subtotal

            # Allocate warehouse without coordinates
            allocation = allocate_warehouse(
                tenant=tenant,
                product=product,
                quantity=quantity,
                customer_latitude=None,
                customer_longitude=None,
            )

            if allocation is None:
                raise serializers.ValidationError(
                    f"No warehouse has enough stock for {product.name}"
                )

            inventory = allocation["inventory"]
            warehouse = allocation["warehouse"]

            OrderItem.objects.create(
                order=order,
                product=product,
                warehouse=warehouse,
                quantity=quantity,
                unit_price=product.price,
            )

            # Update inventory
            inventory.quantity -= quantity
            inventory.save()

            # Update product quantity if it exists
            if hasattr(product, "quantity"):
                product.quantity -= quantity
                product.save()

        # Set order totals
        order.original_amount = total_price
        order.total_price = total_price
        order.save()

        # Create invoice
        Invoice.objects.create(
            order=order,
            invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
        )

        return order


# Default serializer alias
OrderSerializer = OrderCustomerSerializer