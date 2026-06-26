# from django.utils.functional import SimpleLazyObject


# def _resolve_tenant(request):
#     """
#     Figures out which tenant this request belongs to.

#     Priority:
#     1. X-Tenant-Slug header  (e.g. from a frontend or Postman)
#     2. ?tenant= query param  (handy for quick testing)
#     3. The authenticated user's own tenant (if they are a vendor admin)

#     Returns None if no tenant can be identified or if the DB is not
#     yet migrated (e.g. first deploy on Railway before migrate runs).
#     """
#     try:
#         from tenants.models import Tenant

#         slug = (
#             request.headers.get('X-Tenant-Slug')
#             or request.GET.get('tenant')
#         )

#         if slug:
#             try:
#                 return Tenant.objects.get(slug=slug, is_active=True)
#             except Tenant.DoesNotExist:
#                 return None

#         if hasattr(request, 'user') and request.user.is_authenticated:
#             try:
#                 return request.user.owned_tenant
#             except Exception:
#                 pass

#         return None
#     except Exception:
#         # DB not migrated yet or any other infrastructure error —
#         # return None so the request can still proceed (public endpoints work).
#         return None


# class TenantMiddleware:
#     """
#     Sets request.tenant on every incoming request.

#     Views can then do:
#         tenant = request.tenant        # may be None for platform admins
#     """
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         request.tenant = SimpleLazyObject(lambda: _resolve_tenant(request))
#         return self.get_response(request)


# from django.utils.functional import SimpleLazyObject


# def _resolve_tenant(request):
#     try:
#         from tenants.models import Tenant, TenantMember

#         slug = request.headers.get("X-Tenant-Slug") or request.GET.get("tenant")

#         # 1. Resolve tenant from header or query param
#         if slug:
#             tenant = Tenant.objects.filter(
#                 slug=slug,
#                 is_active=True,
#                 status=Tenant.STATUS_APPROVED
#             ).first()

#             if not tenant:
#                 return None

#             return tenant

#         # 2. Resolve tenant from logged-in vendor owner or member
#         if request.user.is_authenticated:
#             owned = getattr(request.user, "owned_tenant", None)

#             if (
#                 owned
#                 and owned.is_active
#                 and owned.status == Tenant.STATUS_APPROVED
#             ):
#                 return owned

#             membership = TenantMember.objects.filter(
#                 user=request.user,
#                 is_active=True,
#                 tenant__is_active=True,
#                 tenant__status=Tenant.STATUS_APPROVED
#             ).select_related("tenant").first()

#             if membership:
#                 return membership.tenant

#         return None

#     except Exception:
#         return None


# class TenantMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         print("HEADERS:", dict(request.headers))
#         print("X-Tenant-Slug:", request.headers.get("X-Tenant-Slug"))

#         request.tenant = SimpleLazyObject(lambda: _resolve_tenant(request))
#         return self.get_response(request)


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
