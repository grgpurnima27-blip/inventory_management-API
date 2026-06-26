from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema

from products.models import Product

from .models import Cart, CartItem
from .serializers import (
    CartSerializer,
    AddToCartSerializer
)


@extend_schema(
    tags=['Cart']
)
class CartView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        cart, _ = Cart.objects.get_or_create(
            user=request.user
        )

        serializer = CartSerializer(cart)

        return Response(serializer.data)


@extend_schema(
    request=AddToCartSerializer,
    tags=['Cart']
)
class AddToCartView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = AddToCartSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        product_id = serializer.validated_data[
            'product_id'
        ]

        quantity = serializer.validated_data[
            'quantity'
        ]

        product = get_object_or_404(
            Product,
            id=product_id
        )

        total_stock = sum(
            inventory.quantity
            for inventory in product.inventories.all()
        )

        if quantity > total_stock:

            return Response(
                {
                    'error':
                    'Insufficient stock.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        cart, _ = Cart.objects.get_or_create(
            user=request.user
        )

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                'quantity': quantity
            }
        )

        if not created:

            new_quantity = (
                item.quantity + quantity
            )

            if new_quantity > total_stock:

                return Response(
                    {
                        'error':
                        'Quantity exceeds stock.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            item.quantity = new_quantity
            item.save()

        return Response(
            {
                'message':
                'Product added to cart.'
            },
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=['Cart']
)
class UpdateCartItemView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):

        item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__user=request.user
        )

        quantity = int(
            request.data.get('quantity', 1)
        )

        total_stock = sum(
            inventory.quantity
            for inventory in item.product.inventories.all()
        )

        if quantity > total_stock:

            return Response(
                {
                    'error':
                    'Insufficient stock.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        item.quantity = quantity
        item.save()

        return Response(
            {
                'message':
                'Cart updated.'
            }
        )


@extend_schema(
    tags=['Cart']
)
class RemoveCartItemView(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, item_id):

        item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__user=request.user
        )

        item.delete()

        return Response(
            {
                'message':
                'Item removed.'
            }
        )
















