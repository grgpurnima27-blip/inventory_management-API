from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, VendorOrderViewSet
from django.urls import path, include

router = DefaultRouter()

# router.register('', OrderViewSet)
router.register(
    r'orders',
    OrderViewSet,
    basename='orders'
)
router.register(
    r"vendor/orders",
    VendorOrderViewSet,
    basename="vendor-orders"
)
router.register(
    "invoices",
    InvoiceViewSet,
    basename="invoices",
)

urlpatterns = router.urls

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
]