from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiResponse

from config.permissions import IsPlatformAdmin, IsTenantOwner
from .models import Tenant, TenantMember
from .serializers import TenantSerializer, TenantMemberSerializer


# ── Tenant CRUD (platform admin only) ────────────────────────────────────────

class TenantViewSet(viewsets.ModelViewSet):
    """
    CRUD for Tenants (vendor stores).

    Who can use this:
      - Platform admin (is_staff=True) — full CRUD + approve/reject
      - Any authenticated user — GET /api/tenants/me/ to read their own tenant

    Filter pending stores: GET /api/tenants/?is_active=false
    """
    queryset         = Tenant.objects.select_related('owner').order_by('name')
    serializer_class = TenantSerializer
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields    = ['name', 'slug', 'owner__username', 'owner__email']
    ordering_fields  = ['name', 'created_at']

    def get_permissions(self):
        if self.action == 'me':
            return [IsAuthenticated()]
        return [IsPlatformAdmin()]

    @extend_schema(
        summary='List all stores',
        description=(
            'Returns all vendor stores. Use `?is_active=false` to see pending registrations '
            'that need approval.'
        ),
        parameters=[
            OpenApiParameter('is_active', bool, description='Filter by active status. false = pending stores.'),
            OpenApiParameter('search', str, description='Search by name, slug, or owner username/email.'),
        ],
        tags=['Tenants'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Create a store (admin)',
        description='Manually register a vendor store. Use vendor/register for self-registration.',
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

    @extend_schema(
        summary='Approve a vendor store',
        description=(
            'Activate a pending vendor store. '
            'The vendor will then be able to log in and use the API.'
        ),
        request=None,
        responses={
            200: OpenApiResponse(description='Store approved and activated.'),
            400: OpenApiResponse(description='Store is already active.'),
        },
        tags=['Tenants'],
    )
    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        tenant = self.get_object()
        if tenant.is_active:
            return Response(
                {'detail': 'This store is already active.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        tenant.is_active = True
        tenant.save(update_fields=['is_active'])
        return Response(
            {
                'detail': f'Store "{tenant.name}" has been approved and is now active.',
                'store': {
                    'id':   tenant.id,
                    'name': tenant.name,
                    'slug': tenant.slug,
                },
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary='Reject a vendor store',
        description=(
            'Reject and delete a pending vendor store registration. '
            'The vendor\'s user account is kept so they can re-apply. '
            'Only works on inactive (pending) stores.'
        ),
        request=None,
        responses={
            200: OpenApiResponse(description='Store registration rejected and deleted.'),
            400: OpenApiResponse(description='Cannot reject an already active store.'),
        },
        tags=['Tenants'],
    )
    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        tenant = self.get_object()
        if tenant.is_active:
            return Response(
                {
                    'detail': (
                        'This store is already active. '
                        'Use DELETE /api/tenants/{id}/ to remove an active store.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        owner_username = tenant.owner.username
        store_name     = tenant.name
        tenant.delete()
        return Response(
            {
                'detail': (
                    f'Store registration for "{store_name}" (owner: {owner_username}) '
                    f'has been rejected and removed. '
                    f'The owner\'s account has been kept — they can re-apply.'
                )
            },
            status=status.HTTP_200_OK,
        )


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
