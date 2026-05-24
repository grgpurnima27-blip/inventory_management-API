"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin

from django.urls import path, include

from rest_framework.routers import DefaultRouter

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from products.views import ProductViewSet
from warehouses.views import WarehouseViewSet
from inventory.views import InventoryViewSet
from orders.views import OrderViewSet
from reports.views import InventorySummaryAPIView


router = DefaultRouter()

router.register(
    'products',
    ProductViewSet,
    basename='products'
)

router.register(
    'warehouses',
    WarehouseViewSet,
    basename='warehouses'
)

router.register(
    'inventory',
    InventoryViewSet,
    basename='inventory'
)

router.register(
    'orders',
    OrderViewSet,
    basename='orders'
)


urlpatterns = [

    path('admin/', admin.site.urls),

    path('api/', include(router.urls)),

    path(
        'api/reports/inventory-summary/',
        InventorySummaryAPIView.as_view(),
        name='inventory-summary'
    ),

    path(
        'api/auth/register/',
        include('accounts.urls')
    ),

    path(
        'api/token/',
        TokenObtainPairView.as_view(),
        name='token_obtain_pair'
    ),

    path(
        'api/token/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh'
    ),

    path(
        'api/schema/',
        SpectacularAPIView.as_view(),
        name='schema'
    ),

    path(
        'swagger/',
        SpectacularSwaggerView.as_view(
            url_name='schema'
        ),
        name='swagger-ui'
    ),
]