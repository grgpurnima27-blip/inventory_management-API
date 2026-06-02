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
    
    # NEW: Accept 'create_items' as an alias for items during creation
    create_items = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text='Alias for items field - accepts same structure'
    )

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
            'create_items',  
        ]
        read_only_fields = ['status', 'payment_status', 'created_at']

    def create(self, validated_data):
        
        items_data = validated_data.pop('items', [])
        if not items_data:
            items_data = validated_data.pop('create_items', [])
        
        order = Order.objects.create(**validated_data)
        
        for item_data in items_data:
            product_id = item_data.get('product')
            quantity = item_data.get('quantity')
            

            product = Product.objects.get(id=product_id)

            warehouse = Warehouse.objects.first()  
            
            OrderItem.objects.create(
                order=order,
                product_id=product_id,
                warehouse=warehouse,
                quantity=quantity,
                unit_price=product.price
            )
            
            # Update order total
            order.original_amount += product.price * quantity
            order.total_price = order.original_amount - order.discount_amount
            order.save()
        
        return order