from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema

from products.models import Product
from .models import Cart, CartItem
from .serializers import CartSerializer, AddToCartSerializer, UpdateCartItemSerializer,CartCheckoutSerializer
from decimal import Decimal

from inventory.models import Inventory
from orders.models import Order, OrderItem


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


@extend_schema(tags=["Cart"])
class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart = Cart.objects.prefetch_related(
            "items__product__tenant",
            "items__product__inventories",
        ).get(id=cart.id)

        serializer = CartSerializer(cart)
        return Response(serializer.data)


@extend_schema(request=AddToCartSerializer, tags=["Cart"])
class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data["product_id"]
        quantity = serializer.validated_data["quantity"]

        product = get_object_or_404(
            Product.objects.select_related("tenant").prefetch_related("inventories"),
            id=product_id,
        )

        error = validate_product_can_be_added(product)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        available_stock = get_product_available_stock(product)

        if quantity > available_stock:
            return Response(
                {
                    "error": "Insufficient stock.",
                    "available_stock": available_stock,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart, _ = Cart.objects.get_or_create(user=request.user)

        item, created = CartItem.objects.select_for_update().get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )

        if not created:
            new_quantity = item.quantity + quantity

            if new_quantity > available_stock:
                return Response(
                    {
                        "error": "Quantity exceeds stock.",
                        "available_stock": available_stock,
                        "current_cart_quantity": item.quantity,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            item.quantity = new_quantity
            item.save(update_fields=["quantity"])

        return Response(
            {
                "message": "Product added to cart.",
                "cart_item_id": item.id,
                "product_id": product.id,
                "vendor_id": product.tenant_id,
                "quantity": item.quantity,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(request=UpdateCartItemSerializer, tags=["Cart"])
class UpdateCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, item_id):
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data["quantity"]

        item = get_object_or_404(
            CartItem.objects.select_for_update().select_related("product__tenant"),
            id=item_id,
            cart__user=request.user,
        )

        error = validate_product_can_be_added(item.product)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        available_stock = get_product_available_stock(item.product)

        if quantity > available_stock:
            return Response(
                {
                    "error": "Insufficient stock.",
                    "available_stock": available_stock,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        item.quantity = quantity
        item.save(update_fields=["quantity"])

        return Response(
            {
                "message": "Cart updated.",
                "cart_item_id": item.id,
                "quantity": item.quantity,
            }
        )


@extend_schema(tags=["Cart"])
class RemoveCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, item_id):
        item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__user=request.user,
        )
        item.delete()

        return Response({"message": "Item removed."})
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