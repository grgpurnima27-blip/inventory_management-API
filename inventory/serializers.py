from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Inventory, InventoryTransaction


class InventorySerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
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
        read_only_fields = ['id', 'stock_status']

    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")
        return value

    def validate(self, attrs):
        product = attrs.get('product')
        warehouse = attrs.get('warehouse')

        qs = Inventory.objects.filter(product=product, warehouse=warehouse)

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "Inventory already exists for this product and warehouse."
            )

        return attrs

    @extend_schema_field(serializers.CharField)
    def get_stock_status(self, obj):
        if obj.quantity == 0:
            return "Out of Stock"
        elif obj.quantity < 5:
            return "Low Stock"
        return "In Stock"


class InventoryTransactionSerializer(serializers.ModelSerializer):

    inventory_name = serializers.CharField(
        source="inventory.product.name",
        read_only=True
    )

    warehouse_name = serializers.CharField(
        source="inventory.warehouse.name",
        read_only=True
    )

    user = serializers.CharField(
        source="user.username",
        read_only=True
    )

    class Meta:
        model = InventoryTransaction

        # Explicit fields (NO "__all__")
        fields = [
            "id",
            "inventory",
            "inventory_name",
            "warehouse_name",
            "user",
            "transaction_type",
            "quantity",
            "remarks",
            "created_at",
        ]

        read_only_fields = ["created_at", "inventory_name", "warehouse_name", "user"]