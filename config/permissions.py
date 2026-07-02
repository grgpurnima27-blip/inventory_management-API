from rest_framework.permissions import BasePermission, SAFE_METHODS
from tenants.models import TenantMember


class IsPlatformAdmin(BasePermission):
    """
    Platform-level admin only (is_staff=True).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff
        )


class IsVendorAdmin(BasePermission):
    """
    Grants write access to store data for:
      - The tenant owner (Tenant.owner == request.user)
      - TenantMember with role 'manager' or 'staff'
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return False

        # Tenant owner
        try:
            if request.user.owned_tenant == tenant:
                return True
        except Exception:
            pass

        # Employees with write-level roles
        return TenantMember.objects.filter(
            tenant=tenant,
            user=request.user,
            is_active=True,
            role__in=[
                TenantMember.ROLE_MANAGER,
                TenantMember.ROLE_STAFF
            ]
        ).exists()


class IsTenantOwner(BasePermission):
    """
    Only the owner of the current request's tenant.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return False

        try:
            return request.user.owned_tenant == tenant
        except Exception:
            return False


class IsAdminOrReadOnly(BasePermission):
    """
    Public read access, admin write access.
    """
    def has_permission(self, request, view):

        if request.method in SAFE_METHODS:
            return True

        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsAdminRole(BasePermission):
    """
    Admin only access.
    """
    def has_permission(self, request, view):

        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsAuthenticatedCustomer(BasePermission):
    """
    Any authenticated user.
    """
    def has_permission(self, request, view):

        return (
            request.user and
            request.user.is_authenticated
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Admin can access everything, user only their own object.
    """
    def has_object_permission(self, request, view, obj):

        if request.user.role == 'admin':
            return True

        return obj.user == request.user