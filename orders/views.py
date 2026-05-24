from django.db import transaction

from rest_framework import viewsets

from rest_framework.decorators import action

from rest_framework.response import Response

from rest_framework.permissions import IsAuthenticated

from .models import Order

from .serializers import OrderSerializer

from inventory.models import Inventory


class OrderViewSet(viewsets.ModelViewSet):

    serializer_class = OrderSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return Order.objects.filter(

            user=self.request.user

        ).prefetch_related(

            'items',
            'items__product',
            'items__warehouse'
        )

    @transaction.atomic
    @action(detail=True, methods=['post'])

    def cancel(self, request, pk=None):

        order = self.get_object()

        if order.status == Order.STATUS_CANCELLED:

            return Response({

                'message':
                'Order already cancelled.'
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

            'message':
            'Order cancelled successfully.'
        })