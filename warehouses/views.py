from rest_framework import viewsets

from config.permissions import IsAdminOrReadOnly

from .models import Warehouse
from .serializers import WarehouseSerializer


class WarehouseViewSet(viewsets.ModelViewSet):

    queryset = Warehouse.objects.all()

    serializer_class = WarehouseSerializer

    permission_classes = [IsAdminOrReadOnly]