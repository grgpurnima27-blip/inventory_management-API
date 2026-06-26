from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncMonth, TruncDay
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.utils import timezone
from datetime import timedelta

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from drf_spectacular.utils import extend_schema, OpenApiResponse

from config.permissions import IsAdminRole
from inventory.models import Inventory
from orders.models import Order, OrderItem
from products.models import Product
from accounts.models import CustomUser
from tenants.mixins import TenantViewMixin
from rest_framework.permissions import IsAuthenticated


# Added here a  serializer for InventorySummaryAPIView
class InventorySummarySerializer(serializers.Serializer):
    total_products = serializers.IntegerField()
    total_inventory = serializers.IntegerField()
    low_stock_products = serializers.IntegerField()
    out_of_stock_products = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()


class InventorySummaryAPIView(APIView):
    permission_classes = [IsAdminRole]
    # Add serializer_class to fix warning
    serializer_class = InventorySummarySerializer

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
            'total_products': total_products,
            'total_inventory': total_inventory,
            'low_stock_products': low_stock_products,
            'out_of_stock_products': out_of_stock_products,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            'cancelled_orders': cancelled_orders,
        })


class TopProductsReportAPIView(APIView):
    """
    Top 10 best selling products by quantity sold.
    Filter by date range: ?days=30
    """
    permission_classes = [IsAdminRole]

    @extend_schema(
        summary='Top Selling Products (Admin only)',
        description='Top 10 products by quantity sold. Filter with ?days=30',
        responses={200: OpenApiResponse(description='Top products returned.')},
        tags=['reports']
    )
    @method_decorator(cache_page(60))
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)

        top_products = (
            OrderItem.objects
            .filter(
                order__status=Order.STATUS_COMPLETED,
                order__created_at__gte=since
            )
            .values(
                'product__id',
                'product__name',
                'product__category',
                'product__price',
            )
            .annotate(
                total_quantity_sold=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('unit_price')),
                total_orders=Count('order', distinct=True),
            )
            .order_by('-total_quantity_sold')[:10]
        )

        return Response({
            'period_days': days,
            'top_products': [
                {
                    'product_id': p['product__id'],
                    'product_name': p['product__name'],
                    'category': p['product__category'],
                    'price': str(p['product__price']),
                    'total_quantity_sold': p['total_quantity_sold'],
                    'total_revenue': str(round(p['total_revenue'], 2)),
                    'total_orders': p['total_orders'],
                }
                for p in top_products
            ]
        })


class RevenueByCityAPIView(APIView):
    """
    Revenue breakdown by delivery city.
    Filter by date range: ?days=30
    """
    permission_classes = [IsAdminRole]

    @extend_schema(
        summary='Revenue by City (Admin only)',
        description='Total revenue grouped by delivery city. Filter with ?days=30',
        responses={200: OpenApiResponse(description='Revenue by city returned.')},
        tags=['reports']
    )
    @method_decorator(cache_page(60))
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)

        revenue_by_city = (
            Order.objects
            .filter(
                status=Order.STATUS_COMPLETED,
                created_at__gte=since
            )
            .values('delivery_city')
            .annotate(
                total_revenue=Sum('total_price'),
                total_orders=Count('id'),
                avg_order_value=Avg('total_price'),
            )
            .order_by('-total_revenue')
        )

        return Response({
            'period_days': days,
            'revenue_by_city': [
                {
                    'city': r['delivery_city'],
                    'total_revenue': str(round(r['total_revenue'], 2)),
                    'total_orders': r['total_orders'],
                    'avg_order_value': str(round(r['avg_order_value'], 2)),
                }
                for r in revenue_by_city
            ]
        })


class TopCustomersReportAPIView(APIView):
    """
    Top 10 customers by total spending.
    Filter by date range: ?days=30
    """
    permission_classes = [IsAdminRole]

    @extend_schema(
        summary='Top Customers (Admin only)',
        description='Top 10 customers by total spending. Filter with ?days=30',
        responses={200: OpenApiResponse(description='Top customers returned.')},
        tags=['reports']
    )
    @method_decorator(cache_page(60))
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)

        top_customers = (
            Order.objects
            .filter(
                status=Order.STATUS_COMPLETED,
                created_at__gte=since
            )
            .values(
                'user__id',
                'user__username',
                'user__email',
            )
            .annotate(
                total_spent=Sum('total_price'),
                total_orders=Count('id'),
                avg_order_value=Avg('total_price'),
            )
            .order_by('-total_spent')[:10]
        )

        return Response({
            'period_days': days,
            'top_customers': [
                {
                    'user_id': c['user__id'],
                    'username': c['user__username'],
                    'email': c['user__email'],
                    'total_spent': str(round(c['total_spent'], 2)),
                    'total_orders': c['total_orders'],
                    'avg_order_value': str(round(c['avg_order_value'], 2)),
                }
                for c in top_customers
            ]
        })


class SalesChartReportAPIView(APIView):
    """
    Daily or monthly sales chart data.
    ?period=daily or ?period=monthly
    ?days=30
    """
    permission_classes = [IsAdminRole]

    @extend_schema(
        summary='Sales Chart Data (Admin only)',
        description=(
            'Daily or monthly revenue chart. '
            'Use ?period=daily or ?period=monthly and ?days=30'
        ),
        responses={200: OpenApiResponse(description='Sales chart data returned.')},
        tags=['reports']
    )
    @method_decorator(cache_page(60))
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        period = request.query_params.get('period', 'daily')
        since = timezone.now() - timedelta(days=days)

        orders = Order.objects.filter(
            status=Order.STATUS_COMPLETED,
            created_at__gte=since
        )

        # Group by day or month
        if period == 'monthly':
            chart_data = (
                orders
                .annotate(period=TruncMonth('created_at'))
                .values('period')
                .annotate(
                    revenue=Sum('total_price'),
                    orders=Count('id'),
                )
                .order_by('period')
            )
        else:
            chart_data = (
                orders
                .annotate(period=TruncDay('created_at'))
                .values('period')
                .annotate(
                    revenue=Sum('total_price'),
                    orders=Count('id'),
                )
                .order_by('period')
            )

        return Response({
            'period': period,
            'days': days,
            'chart': [
                {
                    'date': entry['period'].strftime(
                        '%Y-%m-%d' if period == 'daily' else '%Y-%m'
                    ),
                    'revenue': str(round(entry['revenue'], 2)),
                    'orders': entry['orders'],
                }
                for entry in chart_data
            ]
        })


class CouponUsageReportAPIView(APIView):
    """
    Coupon usage stats — which coupons are used most.
    """
    permission_classes = [IsAdminRole]

    @extend_schema(
        summary='Coupon Usage Report (Admin only)',
        description='See which coupons are used most and total discount given.',
        responses={200: OpenApiResponse(description='Coupon usage returned.')},
        tags=['reports']
    )
    @method_decorator(cache_page(60))
    def get(self, request):
        from coupons.models import Coupon

        coupons = Coupon.objects.annotate(
            total_discount_given=Sum(
                'id',  # placeholder — too see note below
            )
        ).values(
            'code',
            'discount_type',
            'discount_value',
            'used_count',
            'max_uses',
            'is_active',
            'expires_at',
        ).order_by('-used_count')

        return Response({
            'coupons': [
                {
                    'code': c['code'],
                    'discount_type': c['discount_type'],
                    'discount_value': str(c['discount_value']),
                    'used_count': c['used_count'],
                    'max_uses': c['max_uses'],
                    'remaining_uses': c['max_uses'] - c['used_count'],
                    'is_active': c['is_active'],
                    'expires_at': c['expires_at'],
                }
                for c in coupons
            ]
        })
    
class VendorDashboardReportAPIView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Vendor Dashboard Report',
        description='Dashboard stats for the logged-in vendor tenant.',
        tags=['reports']
    )
    def get(self, request):
        tenant = self.get_tenant()

        total_products = Product.objects.filter(
            tenant=tenant
        ).count()

        total_inventory = Inventory.objects.filter(
            tenant=tenant
        ).aggregate(
            total=Sum('quantity')
        )['total'] or 0

        low_stock_products = Inventory.objects.filter(
            tenant=tenant,
            quantity__lt=5,
            quantity__gt=0
        ).count()

        out_of_stock_products = Inventory.objects.filter(
            tenant=tenant,
            quantity=0
        ).count()

        total_orders = Order.objects.filter(
            tenant=tenant
        ).count()

        pending_orders = Order.objects.filter(
            tenant=tenant,
            status=Order.STATUS_PENDING
        ).count()

        completed_orders = Order.objects.filter(
            tenant=tenant,
            status=Order.STATUS_COMPLETED
        ).count()

        cancelled_orders = Order.objects.filter(
            tenant=tenant,
            status=Order.STATUS_CANCELLED
        ).count()

        revenue = Order.objects.filter(
            tenant=tenant,
            status=Order.STATUS_COMPLETED
        ).aggregate(
            total=Sum('total_price')
        )['total'] or 0

        recent_orders = Order.objects.filter(
            tenant=tenant
        ).order_by('-created_at')[:5]

        return Response({
            'tenant': {
                'id': tenant.id,
                'name': tenant.name,
                'slug': tenant.slug,
            },
            'products': {
                'total_products': total_products,
            },
            'inventory': {
                'total_inventory': total_inventory,
                'low_stock_products': low_stock_products,
                'out_of_stock_products': out_of_stock_products,
            },
            'orders': {
                'total_orders': total_orders,
                'pending_orders': pending_orders,
                'completed_orders': completed_orders,
                'cancelled_orders': cancelled_orders,
            },
            'revenue': {
                'completed_order_revenue': str(revenue),
            },
            'recent_orders': [
                {
                    'id': order.id,
                    'customer_name': order.customer_name,
                    'delivery_city': order.delivery_city,
                    'status': order.status,
                    'payment_status': order.payment_status,
                    'total_price': str(order.total_price),
                    'created_at': order.created_at,
                }
                for order in recent_orders
            ]
        })