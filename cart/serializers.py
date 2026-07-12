from rest_framework import serializers

from .models import (
    Cart,
    CartItem,
    SavedItem,
)

from products.models import Product


# ---------------------------------------------------------
# Product (inside cart)
# ---------------------------------------------------------

class CartProductSerializer(serializers.ModelSerializer):

    vendor = serializers.CharField(
        source="tenant.name",
        read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
            "quantity",
            "vendor",
        ]


# ---------------------------------------------------------
# Cart Item
# ---------------------------------------------------------

class CartItemSerializer(serializers.ModelSerializer):

    product = CartProductSerializer(read_only=True)

    subtotal = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "quantity",
            "subtotal",
        ]


# ---------------------------------------------------------
# Cart
# ---------------------------------------------------------

class CartSerializer(serializers.ModelSerializer):

    items = CartItemSerializer(
        many=True,
        read_only=True
    )

    total_items = serializers.ReadOnlyField()

    subtotal = serializers.ReadOnlyField()

    discount_amount = serializers.ReadOnlyField()

    total = serializers.ReadOnlyField()

    coupon = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "total_items",
            "subtotal",
            "discount_amount",
            "total",
            "coupon",
        ]

    def get_coupon(self, obj):
        if obj.applied_coupon:
            return obj.applied_coupon.code
        return None


# ---------------------------------------------------------
# Add To Cart
# ---------------------------------------------------------

class AddToCartSerializer(serializers.Serializer):

    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all()
    )

    quantity = serializers.IntegerField(
        min_value=1
    )


# ---------------------------------------------------------
# Update Cart Item
# ---------------------------------------------------------

class UpdateCartItemSerializer(serializers.Serializer):

    quantity = serializers.IntegerField(
        min_value=1
    )


# ---------------------------------------------------------
# Saved Item
# ---------------------------------------------------------

class SavedItemSerializer(serializers.ModelSerializer):

    product = CartProductSerializer(
        read_only=True
    )

    subtotal = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = SavedItem
        fields = [
            "id",
            "product",
            "quantity",
            "subtotal",
            "created_at",
        ]


# ---------------------------------------------------------
# Checkout
# ---------------------------------------------------------

class CartCheckoutSerializer(serializers.Serializer):

    customer_name = serializers.CharField(
        max_length=200
    )

    payment_method = serializers.ChoiceField(
        choices=[
            ("COD", "Cash on Delivery"),
            ("ESEWA", "eSewa"),
            ("KHALTI", "Khalti"),
        ]
    )

    delivery_city = serializers.CharField(
        required=False,
        allow_blank=True
    )

class MoveToCartSerializer(serializers.Serializer):
    saved_item_id = serializers.IntegerField(
        help_text="ID of the saved item to move back to cart."
    )

class SaveForLaterSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()