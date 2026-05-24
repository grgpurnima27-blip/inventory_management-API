from django.db import transaction

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from config.permissions import IsAdminOrReadOnly

from .models import Order
from .serializers import OrderSerializer
from inventory.models import Inventory


class OrderViewSet(viewsets.ModelViewSet):

    serializer_class = OrderSerializer

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        # Admins can see and manage all orders
        # Customers can only create and view their own orders
        # But both must be authenticated
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        # Admins see ALL orders
        if hasattr(user, 'role') and user.role == 'admin':
            return Order.objects.all().prefetch_related(
                'items',
                'items__product',
                'items__warehouse'
            )

        # Customers only see THEIR OWN orders
        return Order.objects.filter(
            user=user
        ).prefetch_related(
            'items',
            'items__product',
            'items__warehouse'
        )

    def perform_create(self, serializer):
        # Automatically assign logged in user as order owner
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        # Only admins can update orders
        if not (hasattr(request.user, 'role') and request.user.role == 'admin'):
            return Response(
                {'error': 'Only admins can update orders.'},
                status=403
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Only admins can delete orders
        if not (hasattr(request.user, 'role') and request.user.role == 'admin'):
            return Response(
                {'error': 'Only admins can delete orders.'},
                status=403
            )
        return super().destroy(request, *args, **kwargs)

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):

        order = self.get_object()

        # Customers can only cancel their own orders
        if (
            hasattr(request.user, 'role') and
            request.user.role != 'admin' and
            order.user != request.user
        ):
            return Response(
                {'error': 'You can only cancel your own orders.'},
                status=403
            )

        if order.status == Order.STATUS_CANCELLED:
            return Response({
                'message': 'Order already cancelled.'
            })

        for item in order.items.all():

            inventory = Inventory.objects.select_for_update().get(
                product=item.product,
                warehouse=item.warehouse
            )

            inventory.quantity += item.quantity
            inventory.save()

        order.status = Order.STATUS_CANCELLED
        order.save()

        return Response({
            'message': 'Order cancelled successfully.'
        })