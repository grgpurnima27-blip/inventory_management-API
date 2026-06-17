from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TenantViewSet, TenantMemberViewSet

router = DefaultRouter()
router.register('tenants', TenantViewSet, basename='tenants')
router.register('tenant-members', TenantMemberViewSet, basename='tenant-members')

urlpatterns = [
    path('', include(router.urls)),
]
