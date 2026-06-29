from rest_framework import serializers
from .models import Cart, CartItem


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, default=1)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_price = serializers.DecimalField(source="product.price", max_digits=10, decimal_places=2, read_only=True)
    vendor_id = serializers.IntegerField(source="product.tenant.id", read_only=True)
    vendor_name = serializers.CharField(source="product.tenant.name", read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id", "product", "product_name", "product_price",
            "vendor_id", "vendor_name", "quantity", "subtotal"
        ]

    def get_subtotal(self, obj):
        return obj.product.price * obj.quantity


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    vendors = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "vendors", "total", "created_at", "updated_at"]

    def get_total(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())

    def get_vendors(self, obj):
        grouped = {}

        for item in obj.items.select_related("product__tenant").all():
            tenant = item.product.tenant
            key = tenant.id if tenant else 0

            if key not in grouped:
                grouped[key] = {
                    "vendor_id": tenant.id if tenant else None,
                    "vendor_name": tenant.name if tenant else "No vendor",
                    "items": [],
                    "subtotal": 0,
                }

            grouped[key]["items"].append(CartItemSerializer(item).data)
            grouped[key]["subtotal"] += item.product.price * item.quantity

        return list(grouped.values())
class CartCheckoutSerializer(serializers.Serializer):
    customer_name = serializers.CharField()
    delivery_city = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(
        choices=["cod", "esewa", "khalti"],
        default="cod"
    )