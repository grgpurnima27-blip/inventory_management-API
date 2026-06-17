from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from config.permissions import IsPlatformAdmin, IsTenantOwner
from .models import Tenant, TenantMember
from .serializers import TenantSerializer, TenantMemberSerializer


# ── Tenant CRUD (platform admin only) ────────────────────────────────────────

class TenantViewSet(viewsets.ModelViewSet):
    """
    CRUD for Tenants (vendor stores).

    Who can use this:
      - Platform admin (is_staff=True) — full CRUD
      - Any authenticated user — GET /api/tenants/me/ to read their own tenant
    """
    queryset         = Tenant.objects.select_related('owner')
    serializer_class = TenantSerializer

    def get_permissions(self):
        if self.action == 'me':
            return [IsAuthenticated()]
        return [IsPlatformAdmin()]

    @extend_schema(
        summary='List all stores',
        description='Returns all registered vendor tenants. Platform admin only.',
        tags=['Tenants'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Create a store',
        description='Register a new vendor store on the platform. Platform admin only.',
        tags=['Tenants'],
        examples=[
            OpenApiExample(
                name='Create Store Example',
                value={
                    'name': 'TechMart Nepal',
                    'slug': 'techmart',
                    'description': 'Best electronics store in Nepal.',
                    'owner': 1,
                    'is_active': True,
                },
                request_only=True,
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary='Retrieve a store', tags=['Tenants'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary='Update a store', tags=['Tenants'])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(summary='Partial update a store', tags=['Tenants'])
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(summary='Delete a store', tags=['Tenants'])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary='My Store',
        description='Returns the store owned by the currently logged-in vendor admin.',
        responses={200: TenantSerializer},
        tags=['Tenants'],
    )
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        try:
            tenant = request.user.owned_tenant
        except Tenant.DoesNotExist:
            return Response(
                {'error': 'You do not own a store.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(TenantSerializer(tenant).data)


# ── Tenant Member management (store owner only) ───────────────────────────────

class TenantMemberViewSet(viewsets.ModelViewSet):
    """
    Manage your store's team members.

    Only the store owner can add / update / remove members.
    Requires X-Tenant-Slug header.

    Roles:
      manager — full store access (products, warehouses, inventory, coupons, orders)
      staff   — manage inventory and view orders
      viewer  — read-only access to store data
    """
    serializer_class = TenantMemberSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        return [IsTenantOwner()]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return TenantMember.objects.none()
        return TenantMember.objects.filter(tenant=tenant).select_related('user')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['tenant'] = getattr(self.request, 'tenant', None)
        return ctx

    @extend_schema(
        summary='List team members',
        description='Returns all members of your store.',
        tags=['Team Members'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Add a team member',
        description=(
            'Add a registered user to your store with a role. '
            'The user must already have an account on the platform.'
        ),
        request=TenantMemberSerializer,
        tags=['Team Members'],
        examples=[
            OpenApiExample(
                name='Add manager',
                value={'add_user': 'john_doe', 'role': 'manager'},
                request_only=True,
            ),
            OpenApiExample(
                name='Add staff',
                value={'add_user': 'jane_smith', 'role': 'staff'},
                request_only=True,
            ),
            OpenApiExample(
                name='Add viewer',
                value={'add_user': 'bob_viewer', 'role': 'viewer'},
                request_only=True,
            ),
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary='Update member role',
        description="Change a team member's role or activate/deactivate them.",
        request=TenantMemberSerializer,
        tags=['Team Members'],
        examples=[
            OpenApiExample(
                name='Promote to manager',
                value={'role': 'manager'},
                request_only=True,
            ),
            OpenApiExample(
                name='Deactivate member',
                value={'is_active': False},
                request_only=True,
            ),
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary='Remove a team member',
        description='Remove a user from your store.',
        tags=['Team Members'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
