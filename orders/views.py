from django.db import transaction

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.permissions import IsAuthenticatedCustomer, IsOwnerOrAdmin
from inventory.models import Inventory
from .models import Order
from .serializers import OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):

    serializer_class = OrderSerializer

    # TOKEN REQUIRED — customers and admins
    permission_classes = [IsAuthenticatedCustomer]

    queryset = Order.objects.select_related(
        'user'
    ).prefetch_related(
        'items',
        'items__product',
        'items__warehouse',
    )

    def get_queryset(self):
        user = self.request.user

        # Admin sees ALL orders
        if user.role == 'admin':
            return self.queryset

        # Customer sees only THEIR orders
        return self.queryset.filter(user=user)

    def perform_create(self, serializer):
        # Auto assign logged in user to order
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        # Only admin can update orders
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only admins can update orders.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Only admin can delete orders
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only admins can delete orders.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):

        order = self.get_object()

        # Check ownership — customer can only cancel own orders
        if request.user.role != 'admin' and order.user != request.user:
            return Response(
                {'error': 'You can only cancel your own orders.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Prevent double cancellation
        if order.status == Order.STATUS_CANCELLED:
            return Response(
                {'error': 'Order is already cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Restore inventory
        for item in order.items.all():
            inventory = Inventory.objects.select_for_update().get(
                product=item.product,
                warehouse=item.warehouse
            )
            inventory.quantity += item.quantity
            inventory.save()

        order.status = Order.STATUS_CANCELLED
        order.save()

        return Response(
            {'message': 'Order cancelled successfully. Inventory restored.'},
            status=status.HTTP_200_OK
        )