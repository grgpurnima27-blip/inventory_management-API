from rest_framework.exceptions import PermissionDenied, ValidationError


class TenantViewMixin:
    """
    Add this mixin to any ViewSet or APIView to make it tenant-aware.

    What it does automatically:
    - get_queryset()    → scopes results to request.tenant
    - perform_create()  → stamps new objects with request.tenant
    - get_tenant()      → raises 403 if no tenant can be identified
    """

    def get_tenant(self):
        tenant = getattr(self.request, 'tenant', None)
        if tenant is None:
            raise PermissionDenied(
                'Tenant could not be identified. '
                'Send the X-Tenant-Slug header or log in as a vendor.'
            )
        return tenant

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant is not None:
            return qs.filter(tenant=tenant)
        return qs

    def perform_create(self, serializer):
        tenant = self.get_tenant()
        serializer.save(tenant=tenant)
