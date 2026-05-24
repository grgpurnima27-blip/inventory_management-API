from django.db.models import Sum

from rest_framework.views import APIView
from rest_framework.response import Response

from products.models import Product
from inventory.models import Inventory


class InventorySummaryView(APIView):

    def get(self, request):

        total_products = Product.objects.count()

        total_inventory = Inventory.objects.aggregate(
            total=Sum('quantity')
        )['total'] or 0

        low_stock_products = Inventory.objects.filter(
            quantity__lt=5
        ).count()

        out_of_stock_products = Inventory.objects.filter(
            quantity=0
        ).count()

        return Response({
            'total_products': total_products,
            'total_inventory': total_inventory,
            'low_stock_products': low_stock_products,
            'out_of_stock_products': out_of_stock_products
        })