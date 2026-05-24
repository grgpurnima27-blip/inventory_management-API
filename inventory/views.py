from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets
from rest_framework.filters import OrderingFilter

from .models import Inventory
from .serializers import InventorySerializer


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Inventory.objects.select_related(
        'product',
        'warehouse'
    )

    serializer_class = InventorySerializer

    filter_backends = [
        DjangoFilterBackend,
        OrderingFilter
    ]

    filterset_fields = [
        'product',
        'warehouse',
    ]

    ordering_fields = [
        'quantity',
        'created_at'
    ]

    ordering = ['quantity']

    def get_queryset(self):

        queryset = super().get_queryset()

        low_stock = self.request.query_params.get(
            'low_stock'
        )

        out_of_stock = self.request.query_params.get(
            'out_of_stock'
        )

        if low_stock == 'true':

            queryset = queryset.filter(
                quantity__lt=5,
                quantity__gt=0
            )

        if out_of_stock == 'true':

            queryset = queryset.filter(
                quantity=0
            )

        return queryset