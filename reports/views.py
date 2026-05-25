from django.db.models import Sum
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import IsAdminRole
from inventory.models import Inventory
from orders.models import Order
from products.models import Product


class InventorySummaryAPIView(APIView):

    # ADMIN only
    permission_classes = [IsAdminRole]

    # Cache response for 60 seconds
    @method_decorator(cache_page(60))
    def get(self, request):

        # Product stats
        total_products = Product.objects.count()

        # Inventory stats
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

        # Order stats
        total_orders = Order.objects.count()

        pending_orders = (
            Order.objects.filter(
                status=Order.STATUS_PENDING
            ).count()
        )

        completed_orders = (
            Order.objects.filter(
                status=Order.STATUS_COMPLETED
            ).count()
        )

        cancelled_orders = (
            Order.objects.filter(
                status=Order.STATUS_CANCELLED
            ).count()
        )

        return Response({

            # Product stats
            'total_products': total_products,

            # Inventory stats
            'total_inventory': total_inventory,
            'low_stock_products': low_stock_products,
            'out_of_stock_products': out_of_stock_products,

            # Order stats
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            'cancelled_orders': cancelled_orders,
        })