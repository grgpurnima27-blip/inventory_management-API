from django.db.models import Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import Inventory
from orders.models import Order
from products.models import Product


class VendorDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get_vendor_tenant(self, request):
        user = request.user

        if hasattr(user, "owned_tenant"):
            return user.owned_tenant

        if hasattr(user, "profile") and getattr(user.profile, "tenant", None):
            return user.profile.tenant

        return None

    def get(self, request):
        tenant = self.get_vendor_tenant(request)

        if not tenant:
            return Response(
                {"error": "Vendor tenant not found."},
                status=status.HTTP_403_FORBIDDEN,
            )

        products = Product.objects.filter(tenant=tenant)
        orders = Order.objects.filter(tenant=tenant)
        inventories = Inventory.objects.filter(tenant=tenant)

        total_revenue = orders.filter(
            payment_status="paid"
        ).aggregate(total=Sum("total_price"))["total"] or 0

        total_stock = inventories.aggregate(
            total=Sum("quantity")
        )["total"] or 0

        return Response({
            "vendor": {
                "id": tenant.id,
                "name": tenant.name,
                "status": getattr(tenant, "status", None),
                "is_active": tenant.is_active,
            },
            "summary": {
                "total_products": products.count(),
                "total_orders": orders.count(),
                "pending_orders": orders.filter(status="pending").count(),
                "processing_orders": orders.filter(status="processing").count(),
                "completed_orders": orders.filter(status="completed").count(),
                "cancelled_orders": orders.filter(status="cancelled").count(),
                "paid_orders": orders.filter(payment_status="paid").count(),
                "pending_payments": orders.filter(payment_status="pending").count(),
                "total_revenue": total_revenue,
                "total_inventory_records": inventories.count(),
                "total_stock": total_stock,
            },
            "recent_orders": list(
                orders.order_by("-created_at")[:5].values(
                    "id",
                    "customer_name",
                    "delivery_city",
                    "status",
                    "payment_status",
                    "payment_method",
                    "total_price",
                    "created_at",
                )
            ),
            "recent_products": list(
                products.order_by("-created_at")[:5].values(
                    "id",
                    "name",
                    "sku",
                    "price",
                    "quantity",
                    "status",
                    "created_at",
                )
            ),
        })