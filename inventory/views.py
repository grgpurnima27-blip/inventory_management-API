from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets

from .models import Inventory
from .serializers import InventorySerializer


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Inventory.objects.select_related(
        'product',
        'warehouse'
    )

    serializer_class = InventorySerializer

    filter_backends = [DjangoFilterBackend]

    filterset_fields = [
        'product',
        'warehouse',
    ]

    def get_queryset(self):

        queryset = super().get_queryset()

        low_stock = self.request.query_params.get('low_stock')

        if low_stock == 'true':

            queryset = queryset.filter(quantity__lt=5)

        return queryset