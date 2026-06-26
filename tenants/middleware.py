

from django.utils.functional import SimpleLazyObject


def _resolve_tenant(request):
    from tenants.models import Tenant, TenantMember

    slug = request.headers.get("X-Tenant-Slug") or request.GET.get("tenant")

    print("RESOLVING TENANT")
    print("slug =", slug)

    if slug:
        tenant = Tenant.objects.filter(
            slug=slug,
            is_active=True,
            status=Tenant.STATUS_APPROVED
        ).first()

        print("tenant found =", tenant)

        return tenant

    if request.user.is_authenticated:
        owned = getattr(request.user, "owned_tenant", None)

        print("owned =", owned)

        if (
            owned
            and owned.is_active
            and owned.status == Tenant.STATUS_APPROVED
        ):
            return owned

        membership = TenantMember.objects.filter(
            user=request.user,
            is_active=True,
            tenant__is_active=True,
            tenant__status=Tenant.STATUS_APPROVED
        ).select_related("tenant").first()

        print("membership =", membership)

        if membership:
            return membership.tenant

    return None


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("HEADERS:", dict(request.headers))
        print("X-Tenant-Slug:", request.headers.get("X-Tenant-Slug"))
        print("QUERY tenant:", request.GET.get("tenant"))

        request.tenant = SimpleLazyObject(lambda: _resolve_tenant(request))
        return self.get_response(request)
