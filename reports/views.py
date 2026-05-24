from django.db.models import Sum
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import Inventory
from products.models import Product


class InventorySummaryAPIView(APIView):

    #Cache this API response for 60 seconds
    @method_decorator(cache_page(60))
    def get(self, request):

        total_products = Product.objects.count()

        total_inventory = (
            Inventory.objects.aggregate(
                total=Sum('quantity')
            )['total'] or 0
        )

        low_stock_products = (
            Inventory.objects.filter(
                quantity__lt=5,
                quantity__gt=0
            ).count()
        )

        out_of_stock_products = (
            Inventory.objects.filter(
                quantity=0
            ).count()
        )

        return Response({
            'total_products': total_products,
            'total_inventory': total_inventory,
            'low_stock_products': low_stock_products,
            'out_of_stock_products': out_of_stock_products,
        })