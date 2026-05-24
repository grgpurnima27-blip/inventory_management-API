from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrReadOnly(BasePermission):
    """
    Admins can do everything.
    Authenticated customers can only read (GET).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # GET, HEAD, OPTIONS — allow all authenticated users
        if request.method in SAFE_METHODS:
            return True
        # Write methods — only admin role
        return request.user.role == 'admin'


class IsAdminRole(BasePermission):
    """Only admin role users — full access"""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )