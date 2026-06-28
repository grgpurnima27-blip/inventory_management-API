from rest_framework.permissions import BasePermission


class IsPaymentOwner(BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.customer == request.user


class IsAdminOrReadOnly(BasePermission):

    def has_permission(self, request, view):

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        return getattr(request.user, "role", None) == "admin"