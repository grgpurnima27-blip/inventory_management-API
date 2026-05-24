from rest_framework import viewsets
from rest_framework import filters
from config.permissions import IsAdminOrReadOnly
from rest_framework.permissions import AllowAny

from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import (
    AllowAny,
    IsAdminUser,
)

from .models import Product
from .serializers import ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):

    queryset = Product.objects.all()

    serializer_class = ProductSerializer

    filter_backends = [

        filters.SearchFilter,

        filters.OrderingFilter,
    ]
    permission_classes= [IsAuthenticated]

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

        if self.action in ['list', 'retrieve']:

            return [AllowAny()]

        return [IsAdminOrReadOnly()]  