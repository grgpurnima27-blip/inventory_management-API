from decimal import Decimal
from rest_framework import serializers
from .models import Invoice, Order, OrderItem
from inventory.services.warehouse_allocator import allocate_warehouse

from django.db import transaction
from products.models import Product
from .models import Invoice
import uuid


class OrderItemSerializer(serializers.ModelSerializer):

    product_name   = serializers.CharField(
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


class OrderCustomerSerializer(serializers.ModelSerializer):
    """
    Customer serializer:
    - Can see their own order
    - Cannot edit status or payment_status
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
            'id',
            'delivery_city',
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
    """
    Admin serializer:
    - Sees everything including updated_at
    - Can update status and payment_status
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
            'id',
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

    def validate_status(self, value):
        order = self.instance
        if not order:
            return value

        valid_transitions = {
            Order.STATUS_PENDING:    [Order.STATUS_PROCESSING, Order.STATUS_CANCELLED],
            Order.STATUS_PROCESSING: [Order.STATUS_SHIPPED,    Order.STATUS_CANCELLED],
            Order.STATUS_SHIPPED:    [Order.STATUS_COMPLETED],
            Order.STATUS_COMPLETED:  [],
            Order.STATUS_CANCELLED:  [],
        }

        allowed = valid_transitions.get(order.status, [])
        if value not in allowed:
            raise serializers.ValidationError(
                f'Cannot move from "{order.status}" to "{value}". '
                f'Allowed transitions: {allowed}'
            )
        return value

    ### UPDATED: uses constants instead of raw strings
    def validate_payment_status(self, value):
        order = self.instance
        if not order:
            return value
        if (
            order.payment_status == Order.PAYMENT_STATUS_PAID and  # ← UPDATED
            value != Order.PAYMENT_STATUS_PAID                     # ← UPDATED
        ):
            raise serializers.ValidationError(
                'Cannot change payment status once it is "paid".'  # ← UPDATED message
            )
        return value

    ###3 UPDATED: uses constants instead of raw strings
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
            if (
                new_payment_status == Order.PAYMENT_STATUS_PAID and      # ← UPDATED
                instance.payment_status != Order.PAYMENT_STATUS_PAID     # ← UPDATED
            ):
                instance.paid_at = timezone.now()
            instance.payment_status = new_payment_status

        instance.save()
        return instance
    


# Default serializer alias
OrderSerializer = OrderCustomerSerializer

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"





class OrderCreateItemSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):

    customer_name = serializers.CharField()
    delivery_city = serializers.CharField()

    delivery_address = serializers.CharField()

    delivery_latitude = serializers.FloatField()

    delivery_longitude = serializers.FloatField()
    payment_method = serializers.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES
    )

    items = OrderCreateItemSerializer(many=True)

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
            delivery_city=validated_data["delivery_city"],
            delivery_address=validated_data["delivery_address"],
            delivery_latitude=validated_data["delivery_latitude"],
            delivery_longitude=validated_data["delivery_longitude"],
            payment_method=validated_data["payment_method"],
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

            allocation = allocate_warehouse(
                tenant=tenant,
                product=product,
                quantity=quantity,
                customer_latitude=validated_data["delivery_latitude"],
                customer_longitude=validated_data["delivery_longitude"],
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

            inventory.quantity -= quantity
            inventory.save()

            if hasattr(product, "quantity"):
                product.quantity -= quantity
                product.save()

        order.original_amount = total_price
        order.total_price = total_price
        order.save()


        print("Creating invoice...")

        invoice = Invoice.objects.create(
            order=order,
            invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
        )

        print("Invoice created:", invoice.id)

        return order