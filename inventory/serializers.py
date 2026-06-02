from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Inventory


class InventorySerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )

    warehouse_name = serializers.CharField(
        source='warehouse.name',
        read_only=True
    )

    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = Inventory
        fields = [
            'id',
            'product',
            'product_name',
            'warehouse',
            'warehouse_name',
            'quantity',
            'stock_status',
        ]
        read_only_fields = [
            'id',
            'stock_status',
        ]

    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError(
                'Quantity cannot be negative.'
            )
        return value

    def validate(self, attrs):
        product = attrs.get('product')
        warehouse = attrs.get('warehouse')

        queryset = Inventory.objects.filter(
            product=product,
            warehouse=warehouse
        )

        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)

        if queryset.exists():
            raise serializers.ValidationError({
                'inventory':
                (
                    f'{product.name} already exists '
                    f'in {warehouse.name}. '
                    f'Please update the existing inventory instead.'
                )
            })

        return attrs

    # Add here @extend_schema_field decorator to fix warning
    @extend_schema_field(serializers.CharField)
    def get_stock_status(self, obj):
        if obj.quantity == 0:
            return 'Out of Stock'
        if obj.quantity < 5:
            return 'Low Stock'
        return 'In Stock'