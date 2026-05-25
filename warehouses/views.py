from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from config.permissions import IsAdminOrReadOnly
from .models import Warehouse
from .serializers import WarehouseSerializer


class WarehouseViewSet(viewsets.ModelViewSet):

    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer

    def get_permissions(self):
        # PUBLIC — no token required
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        # ADMIN only — token required
        return [IsAdminOrReadOnly()]