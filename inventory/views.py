from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets

from config.permissions import IsAdminOrReadOnly

from rest_framework import filters

from .models import Inventory
from .serializers import InventorySerializer


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Inventory.objects.select_related(
        'product',
        'warehouse'
    )

    serializer_class = InventorySerializer

    permission_classes = [IsAdminOrReadOnly]

    filter_backends = [

        DjangoFilterBackend,

        filters.OrderingFilter,
    ]

    filterset_fields = [

        'product',
        'warehouse',
    ]

    ordering_fields = [

        'quantity',
    ]

    def get_queryset(self):

        queryset = super().get_queryset()

        low_stock = self.request.query_params.get(
            'low_stock'
        )

        if low_stock == 'true':

            queryset = queryset.filter(
                quantity__lt=5
            )

        return queryset