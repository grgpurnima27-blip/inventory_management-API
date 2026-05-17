from django.db import transaction

from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from inventory.models import Inventory

from .models import Order
from .serializers import OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):

    queryset = Order.objects.prefetch_related(
        'items',
        'items__product',
        'items__warehouse',
    )

    serializer_class = OrderSerializer

    @transaction.atomic
    @action(detail=True, methods=['post'])

    def cancel(self, request, pk=None):

        order = self.get_object()

        if order.status == 'cancelled':

            return Response(
                {
                    'error': 'Order already cancelled'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        for item in order.items.all():

            inventory = Inventory.objects.select_for_update().get(
                product=item.product,
                warehouse=item.warehouse
            )

            inventory.quantity += item.quantity

            inventory.save()

        order.status = 'cancelled'

        order.save()

        return Response(
            {
                'message': 'Order cancelled successfully'
            }
        )