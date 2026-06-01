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

from accounts.jwt_views import CustomTokenRefreshView

from products.views import ProductViewSet
from warehouses.views import WarehouseViewSet
from inventory.views import InventoryViewSet
from orders.views import OrderViewSet
from wishlist.views import WishlistViewSet

from django.conf import settings
from django.conf.urls.static import static


router = DefaultRouter()

router.register('products', ProductViewSet, basename='products')
router.register('warehouses', WarehouseViewSet, basename='warehouses')
router.register('inventory', InventoryViewSet, basename='inventory')
router.register('orders', OrderViewSet, basename='orders')
router.register('wishlist', WishlistViewSet, basename='wishlist')


urlpatterns = [

    # Admin Panel
    path('admin/', admin.site.urls),

    # Main API
    path('api/', include(router.urls)),

    # Authentication
    path('api/auth/', include('accounts.urls')),

    # JWT Refresh
    path(
        'api/auth/token/refresh/',
        CustomTokenRefreshView.as_view(),
        name='token_refresh'
    ),

    ### Reports — all report endpoints now handled by reports/urls.py
    path('api/reports/', include('reports.urls')),

    # Reviews
    path('api/', include('reviews.urls')),

    # Coupons
    path('api/', include('coupons.urls')),

    # OpenAPI Schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Swagger UI
    path(
        'swagger/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui'
    ),
    path('api/notifications/', include('notifications.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)