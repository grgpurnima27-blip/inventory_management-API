from rest_framework.routers import DefaultRouter
from .views import (
    InventoryViewSet,
    InventoryTransactionViewSet,
)

router = DefaultRouter()

router.register(
    "",
    InventoryViewSet,
)

router.register(
    "inventory-transactions",
    InventoryTransactionViewSet,
    basename="inventory-transactions",
)

urlpatterns = router.urls