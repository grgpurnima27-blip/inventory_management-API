from rest_framework.exceptions import PermissionDenied, ValidationError


class TenantViewMixin:
    """
    Add this mixin to any ViewSet or APIView to make it tenant-aware.

    What it does automatically:
    - get_queryset()    → scopes results to request.tenant
    - perform_create()  → stamps new objects with request.tenant
    - get_tenant()      → raises 403 if no tenant can be identified
    """

    # def get_tenant(self):
    #     tenant = getattr(self.request, 'tenant', None)
    #     # `not tenant` forces the SimpleLazyObject to evaluate its wrapped
    #     # value — `is None` alone won't work because request.tenant is always
    #     # a SimpleLazyObject, never None itself.
    #     if not tenant:
    #         raise PermissionDenied(
    #             'Tenant could not be identified. '
    #             'Send the X-Tenant-Slug header or log in as a vendor.'
    #         )
    #     return tenant
    def get_tenant(self):
        tenant = getattr(self.request, 'tenant', None)

        if tenant:
            return tenant

        slug = (
            self.request.headers.get("X-Tenant-Slug")
            or self.request.query_params.get("tenant")
        )

        if slug:
            from tenants.models import Tenant

            tenant = Tenant.objects.filter(
                slug=slug,
                is_active=True,
                status=Tenant.STATUS_APPROVED
            ).first()

            if tenant:
                return tenant

        raise PermissionDenied(
            'Tenant could not be identified. '
            'Send the X-Tenant-Slug header or log in as a vendor.'
        )

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        # Use `if tenant:` — forces SimpleLazyObject evaluation.
        # `if tenant is not None:` would always be True because request.tenant
        # is always a SimpleLazyObject wrapper, even when it wraps None.
        if tenant:
            return qs.filter(tenant=tenant)
        return qs

    def perform_create(self, serializer):
        tenant = self.get_tenant()
        serializer.save(tenant=tenant)
