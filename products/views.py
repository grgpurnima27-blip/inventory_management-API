from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from config.permissions import IsAdminOrReadOnly
from .models import Product
from .serializers import ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):

    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        'name',
        'category',
        'sku',
    ]

    ordering_fields = [
        'price',
        'created_at',
        'name',
    ]

    def get_permissions(self):
        # PUBLIC — no token required
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        # ADMIN only — token required
        return [IsAdminOrReadOnly()]