from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from config.permissions import IsVendorAdmin
from tenants.mixins import TenantViewMixin
from .models import Warehouse
from .serializers import WarehouseSerializer


class WarehouseViewSet(TenantViewMixin, viewsets.ModelViewSet):

    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsVendorAdmin()]