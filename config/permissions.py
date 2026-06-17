from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS
)


class IsPlatformAdmin(BasePermission):
    """
    Platform-level admin only (is_staff=True).
    Can create/manage Tenants. Cannot touch any vendor data.
    Created via Django's createsuperuser command.
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

    Viewer-role members and unrelated users are denied.
    Requires X-Tenant-Slug header to resolve the tenant.
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
        from tenants.models import TenantMember
        return TenantMember.objects.filter(
            tenant=tenant,
            user=request.user,
            is_active=True,
            role__in=[TenantMember.ROLE_MANAGER, TenantMember.ROLE_STAFF]
        ).exists()


class IsTenantOwner(BasePermission):
    """
    Only the owner of the current request's tenant.
    Used for managing TenantMembers — only the store owner can add/remove staff.
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
    PUBLIC (no token):
    - GET /api/products/
    - GET /api/warehouses/

    ADMIN only:
    - POST, PUT, PATCH, DELETE /api/products/
    - POST, PUT, PATCH, DELETE /api/warehouses/
    - POST, PUT, PATCH, DELETE /api/inventory/
    """

    def has_permission(self, request, view):

        # Public can read without token
        if request.method in SAFE_METHODS:
            return True

        # Must be logged in
        if not request.user or not request.user.is_authenticated:
            return False

        # Only admin can write
        return request.user.role == 'admin'


class IsAdminRole(BasePermission):
    """
    ADMIN only — full access.
    Used for inventory management.
    """

    def has_permission(self, request, view):

        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsAuthenticatedCustomer(BasePermission):
    """
    AUTHENTICATED USERS (customer or admin):
    - POST /api/orders/
    - GET  /api/orders/
    - POST /api/orders/{id}/cancel/
    """

    def has_permission(self, request, view):

        return (
            request.user and
            request.user.is_authenticated
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object level permission:
    - Admin can access any order
    - Customer can only access their own order
    """

    def has_object_permission(self, request, view, obj):

        # Admin sees everything
        if request.user.role == 'admin':
            return True

        # Customer only sees their own
        return obj.user == request.user