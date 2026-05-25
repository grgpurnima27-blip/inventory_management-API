from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS
)


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