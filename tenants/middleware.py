from django.utils.functional import SimpleLazyObject
from tenants.models import Tenant, TenantMember


def _resolve_tenant(request):
    slug = request.headers.get("X-Tenant-Slug") or request.GET.get("tenant")

    if slug:
        return Tenant.objects.filter(slug=slug, is_active=True).first()

    if request.user.is_authenticated:
        return getattr(request.user, "owned_tenant", None)

    return None


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = SimpleLazyObject(lambda: _resolve_tenant(request))
        return self.get_response(request)