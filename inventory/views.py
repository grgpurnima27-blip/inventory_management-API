from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from config.permissions import IsVendorAdmin
from tenants.mixins import TenantViewMixin
from .models import Inventory
from .serializers import InventorySerializer


class InventoryViewSet(TenantViewMixin, viewsets.ModelViewSet):

    queryset = Inventory.objects.select_related(
        'product',
        'warehouse'
    )

    serializer_class = InventorySerializer

    # ADMIN only — full access
    permission_classes = [IsVendorAdmin]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        'product',
        'warehouse',
    ]

    search_fields = [
        'product__name',
        'warehouse__name',
    ]

    ordering_fields = [
        'quantity',
    ]

    ordering = [
        'quantity',
    ]

    def get_queryset(self):

        queryset = super().get_queryset()

        low_stock = self.request.query_params.get('low_stock')

        if low_stock == 'true':
            queryset = queryset.filter(quantity__lt=5)

        return queryset