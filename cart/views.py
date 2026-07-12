from itertools import product

from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from decimal import Decimal
from drf_spectacular.utils import extend_schema
from django.db.models import Sum
from orders.models import Order, OrderItem

from coupons.serializers import ApplyCouponSerializer

from products.models import Product
from inventory.models import Inventory
from .serializers import SavedItemSerializer ,CartCheckoutSerializer

from .models import (
    Cart,
    CartItem,
    SavedItem,
)

from .serializers import (
    CartSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer,
    SavedItemSerializer,
    CartCheckoutSerializer,
    MoveToCartSerializer,
    SaveForLaterSerializer,
)


# ---------------------------------------------------------
# Helper
# ---------------------------------------------------------

def get_user_cart(user):
    """
    Returns the authenticated user's cart.
    Creates one if it doesn't exist.
    """
    cart, created = Cart.objects.get_or_create(user=user)
    return cart
def get_product_available_stock(product):
    inventories = product.inventories.all()

    if product.tenant_id:
        inventories = inventories.filter(tenant=product.tenant)

    stock = inventories.aggregate(total=Sum("quantity"))["total"]

    if stock is not None:
        return stock

    return product.quantity or 0


def validate_product_can_be_added(product):
    if not product.tenant_id:
        return "This product is not connected to any vendor."

    if not product.tenant.is_active:
        return "This vendor is inactive."

    if getattr(product.tenant, "status", None) != "approved":
        return "This vendor is not approved yet."

    return None

# ---------------------------------------------------------
# GET CART
# GET /api/cart/
# ---------------------------------------------------------
@extend_schema(tags=["Cart"])
class CartView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        cart = get_user_cart(request.user)

        serializer = CartSerializer(cart)

        return Response(serializer.data)


# ---------------------------------------------------------
# ADD TO CART
# POST /api/cart/add/
# ---------------------------------------------------------
@extend_schema(request=AddToCartSerializer, tags=["Cart"])
class AddToCartView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        serializer = AddToCartSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        cart = get_user_cart(request.user)

        product = serializer.validated_data["product"]

        quantity = serializer.validated_data["quantity"]

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                "quantity": quantity
            }
        )

        if not created:

            new_quantity = item.quantity + quantity

            if new_quantity > product.stock:

                return Response(
                    {
                        "detail":
                        "Not enough stock available."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            item.quantity = new_quantity
            item.save()

        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_201_CREATED
        )


# ---------------------------------------------------------
# UPDATE CART ITEM
# PATCH /api/cart/item/{id}/
# ---------------------------------------------------------
@extend_schema(request=UpdateCartItemSerializer, tags=["Cart"])
class UpdateCartItemView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):

        cart = get_user_cart(request.user)

        cart_item = get_object_or_404(
            CartItem,
            id=pk,
            cart=cart
        )

        serializer = UpdateCartItemSerializer(
            cart_item,
            data=request.data,
            partial=True,
            context={
                "cart_item": cart_item
            }
        )

        serializer.is_valid(raise_exception=True)

        cart_item.quantity = serializer.validated_data[
            "quantity"
        ]

        cart_item.save()

        return Response(
            CartSerializer(cart).data
        )


# ---------------------------------------------------------
# DELETE CART ITEM
# DELETE /api/cart/item/{id}/
# ---------------------------------------------------------
@extend_schema(tags=["Cart"])
class DeleteCartItemView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request, pk):

        cart = get_user_cart(request.user)

        item = get_object_or_404(
            CartItem,
            id=pk,
            cart=cart
        )

        item.delete()

        return Response(
            {
                "message":
                "Item removed from cart successfully."
            },
            status=status.HTTP_204_NO_CONTENT
        )

# ---------------------------------------------------------
# CLEAR CART
# DELETE /api/cart/clear/
# ---------------------------------------------------------
@extend_schema(tags=["Cart"])
class ClearCartView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request):

        cart = get_user_cart(request.user)

        cart.items.all().delete()

        cart.applied_coupon = None
        cart.save(update_fields=["applied_coupon"])

        return Response(
            {
                "message": "Cart cleared successfully."
            },
            status=status.HTTP_200_OK
        )


# ---------------------------------------------------------
# APPLY COUPON
# POST /api/cart/apply-coupon/
# ---------------------------------------------------------

@extend_schema(
    request=ApplyCouponSerializer,
    tags=["Cart"],
    summary="Apply Coupon",
    description="Apply a coupon to the authenticated user's cart."
)
class ApplyCouponView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        cart = get_user_cart(request.user)

        serializer = ApplyCouponSerializer(
            data=request.data,
            context={
                "request": request
            }
        )

        serializer.is_valid(raise_exception=True)

        coupon = serializer.validated_data["coupon"]

        cart.applied_coupon = coupon
        cart.save(update_fields=["applied_coupon"])

        return Response(
            {
                "message": "Coupon applied successfully.",
                "coupon": coupon.code,
                "discount": serializer.validated_data["discount"],
                "subtotal": cart.subtotal,
                "total": cart.total,
            },
            status=status.HTTP_200_OK
        )


# ---------------------------------------------------------
# REMOVE COUPON
# DELETE /api/cart/remove-coupon/
# ---------------------------------------------------------

@extend_schema(tags=["Cart"])
class RemoveCouponView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request):

        cart = get_user_cart(request.user)

        if cart.applied_coupon is None:

            return Response(
                {
                    "message": "No coupon has been applied."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        cart.applied_coupon = None
        cart.save(update_fields=["applied_coupon"])

        return Response(
            {
                "message": "Coupon removed successfully."
            },
            status=status.HTTP_200_OK
        )


# ---------------------------------------------------------
# CART SUMMARY
# GET /api/cart/summary/
# ---------------------------------------------------------
@extend_schema(tags=["Cart"])
class CartSummaryView(APIView):

    permission_classes = [IsAuthenticated]

    SHIPPING_COST = Decimal("150.00")
    TAX_RATE = Decimal("0.13")

    def get(self, request):

        cart = get_user_cart(request.user)

        subtotal = cart.subtotal
        discount = cart.discount_amount

        taxable_amount = subtotal - discount

        if taxable_amount < Decimal("0.00"):
            taxable_amount = Decimal("0.00")

        tax = taxable_amount * self.TAX_RATE

        grand_total = (
            taxable_amount +
            tax +
            self.SHIPPING_COST
        )

        return Response(
            {
                "total_items": cart.total_items,
                "subtotal": subtotal,
                "discount": discount,
                "shipping": self.SHIPPING_COST,
                "tax": tax.quantize(Decimal("0.01")),
                "grand_total": grand_total.quantize(
                    Decimal("0.01")
                ),
                "coupon": (
                    cart.applied_coupon.code
                    if cart.applied_coupon
                    else None
                )
            }
        )
    
# ---------------------------------------------------------
# SAVE FOR LATER
# POST /api/cart/save-for-later/
# ---------------------------------------------------------

@extend_schema(request=SaveForLaterSerializer, tags=["Cart"])
class SaveForLaterView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        cart = get_user_cart(request.user)

        item_id = request.data.get("item_id")

        if not item_id:
            return Response(
                {
                    "detail": "item_id is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item = get_object_or_404(
            CartItem,
            id=item_id,
            cart=cart
        )

        saved_item, created = SavedItem.objects.get_or_create(
            cart=cart,
            product=cart_item.product,
            defaults={
                "quantity": cart_item.quantity
            }
        )

        if not created:
            saved_item.quantity += cart_item.quantity
            saved_item.save()

        cart_item.delete()

        return Response(
            {
                "message": "Item moved to Save For Later."
            },
            status=status.HTTP_200_OK
        )


# ---------------------------------------------------------
# SAVED ITEMS
# GET /api/cart/saved-items/
# ---------------------------------------------------------
@extend_schema(tags=["Cart"])
class SavedItemsView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        cart = get_user_cart(request.user)

        serializer = SavedItemSerializer(
            cart.saved_items.all(),
            many=True
        )

        return Response(serializer.data)
    

# ---------------------------------------------------------
# MOVE TO CART
# POST /api/cart/move-to-cart/
# ---------------------------------------------------------

@extend_schema(
    request=MoveToCartSerializer,
    tags=["Cart"]
)
class MoveToCartView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        cart = get_user_cart(request.user)

        serializer = MoveToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        saved_item_id = serializer.validated_data["saved_item_id"]

        saved_item = get_object_or_404(
            SavedItem,
            id=saved_item_id,
            cart=cart
        )

        # Get product
        product = saved_item.product

        # Check available quantity
        if product.quantity < saved_item.quantity:
            return Response(
                {
                    "detail": "Not enough stock available."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                "quantity": saved_item.quantity
            }
        )

        if not created:

            new_quantity = (
                cart_item.quantity +
                saved_item.quantity
            )

            if new_quantity > product.quantity:
                return Response(
                    {
                        "detail": "Not enough stock available."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart_item.quantity = new_quantity
            cart_item.save()

        saved_item.delete()

        return Response(
            {
                "message": "Item moved back to cart."
            },
            status=status.HTTP_200_OK
        )

# ---------------------------------------------------------
# DELETE SAVED ITEM
# DELETE /api/cart/saved-items/{id}/
# ---------------------------------------------------------

@extend_schema(tags=["Cart"])
class DeleteSavedItemView(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):

        cart = get_user_cart(request.user)

        saved_item = get_object_or_404(
            SavedItem,
            id=pk,
            cart=cart
        )

        saved_item.delete()

        return Response(
            {
                "message":
                "Saved item deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT
        )
@extend_schema(request=CartCheckoutSerializer, tags=["Cart"])
class CartCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CartCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer_name = serializer.validated_data["customer_name"]
        payment_method = serializer.validated_data["payment_method"]

        delivery_city = serializer.validated_data.get("delivery_city", "").strip()

        if not delivery_city:
            try:
                delivery_city = request.user.profile.city or ""
            except Exception:
                delivery_city = ""

        if not delivery_city:
            return Response(
                {"error": "delivery_city is required or set city in user profile."},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart = Cart.objects.prefetch_related(
            "items__product__tenant"
        ).filter(user=request.user).first()

        if not cart or not cart.items.exists():
            return Response(
                {"error": "Cart is empty."},
                status=status.HTTP_400_BAD_REQUEST
            )

        vendor_groups = {}

        for cart_item in cart.items.all():
            product = cart_item.product
            quantity = cart_item.quantity

            if not product.tenant_id:
                return Response(
                    {"error": f"{product.name} has no vendor."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not product.tenant.is_active:
                return Response(
                    {"error": f"{product.tenant.name} vendor is inactive."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if getattr(product.tenant, "status", None) != "approved":
                return Response(
                    {"error": f"{product.tenant.name} vendor is not approved."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            inventory = Inventory.objects.select_for_update().filter(
                tenant=product.tenant,
                product=product,
                warehouse__tenant=product.tenant,
                warehouse__city__iexact=delivery_city,
                quantity__gte=quantity,
            ).first()

            if not inventory:
                return Response(
                    {
                        "error": (
                            f"{product.name} is not available in "
                            f"{delivery_city} with quantity {quantity}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if product.quantity < quantity:
                return Response(
                    {"error": f"Insufficient product stock for {product.name}."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            tenant_id = product.tenant_id
            unit_price = Decimal(str(product.price))

            if tenant_id not in vendor_groups:
                vendor_groups[tenant_id] = {
                    "tenant": product.tenant,
                    "items": [],
                    "original_amount": Decimal("0.00"),
                }

            vendor_groups[tenant_id]["items"].append({
                "product": product,
                "warehouse": inventory.warehouse,
                "inventory": inventory,
                "quantity": quantity,
                "unit_price": unit_price,
            })

            vendor_groups[tenant_id]["original_amount"] += unit_price * quantity

        created_orders = []

        for group in vendor_groups.values():
            original_amount = group["original_amount"].quantize(Decimal("0.01"))
            discount_amount = Decimal("0.00")
            total_price = original_amount - discount_amount

            order = Order.objects.create(
                tenant=group["tenant"],
                user=request.user,
                customer_name=customer_name,
                delivery_city=delivery_city,
                payment_method=payment_method,
                payment_status=Order.PAYMENT_STATUS_PENDING,
                status=Order.STATUS_PENDING,
                original_amount=original_amount,
                discount_amount=discount_amount,
                total_price=total_price,
            )

            for item in group["items"]:
                OrderItem.objects.create(
                    order=order,
                    product=item["product"],
                    warehouse=item["warehouse"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                )

                inventory = item["inventory"]
                inventory.quantity -= item["quantity"]
                inventory.save(update_fields=["quantity"])

                product = item["product"]
                product.quantity -= item["quantity"]
                product.save(update_fields=["quantity"])

            created_orders.append(order)

        cart.items.all().delete()

        return Response(
            {
                "message": "Cart checkout successful. Vendor orders created.",
                "order_count": len(created_orders),
                "orders": [
                    {
                        "order_id": order.id,
                        "vendor_id": order.tenant_id,
                        "vendor_name": order.tenant.name,
                        "total_price": order.total_price,
                        "status": order.status,
                        "payment_method": order.payment_method,
                    }
                    for order in created_orders
                ],
            },
            status=status.HTTP_201_CREATED
        )