from django.utils.functional import SimpleLazyObject


def _resolve_tenant(request):
    """
    Figures out which tenant this request belongs to.

    Priority:
    1. X-Tenant-Slug header  (e.g. from a frontend or Postman)
    2. ?tenant= query param  (handy for quick testing)
    3. The authenticated user's own tenant (if they are a vendor admin)

    Returns None if no tenant can be identified or if the DB is not
    yet migrated (e.g. first deploy on Railway before migrate runs).
    """
    try:
        from tenants.models import Tenant

        slug = (
            request.headers.get('X-Tenant-Slug')
            or request.GET.get('tenant')
        )

        if slug:
            try:
                return Tenant.objects.get(slug=slug, is_active=True)
            except Tenant.DoesNotExist:
                return None

        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                return request.user.owned_tenant
            except Exception:
                pass

        return None
    except Exception:
        # DB not migrated yet or any other infrastructure error —
        # return None so the request can still proceed (public endpoints work).
        return None


class TenantMiddleware:
    """
    Sets request.tenant on every incoming request.

    Views can then do:
        tenant = request.tenant        # may be None for platform admins
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = SimpleLazyObject(lambda: _resolve_tenant(request))
        return self.get_response(request)
