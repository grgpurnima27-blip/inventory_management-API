from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from config.permissions import IsVendorAdmin
from tenants.mixins import TenantViewMixin

from .models import Inventory, InventoryTransaction
from .serializers import InventorySerializer, InventoryTransactionSerializer


class InventoryViewSet(TenantViewMixin, viewsets.ModelViewSet):

    queryset = Inventory.objects.select_related(
        'product',
        'warehouse'
    )

    serializer_class = InventorySerializer
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


class InventoryTransactionViewSet(
    TenantViewMixin,
    viewsets.ModelViewSet
):
    queryset = InventoryTransaction.objects.select_related(
        "inventory",
        "tenant",
        "remarks"
    )

    serializer_class = InventoryTransactionSerializer
    permission_classes = [IsVendorAdmin]

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.tenant,   # ✅ REQUIRED FIX
            remarks=self.request.user     # optional (your logic)
        )