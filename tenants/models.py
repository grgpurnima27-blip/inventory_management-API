from django.db import models
from django.conf import settings


class Tenant(models.Model):
    """
    Represents one vendor / store on the platform.
    Every piece of business data (products, orders, warehouses …)
    is linked back to a Tenant so that vendors never see each other's data.
    """
    name        = models.CharField(max_length=255, unique=True)
    slug        = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    owner       = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_tenant',
    )
    # is_active   = models.BooleanField(default=True)
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_SUSPENDED = "suspended"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_SUSPENDED, "Suspended"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    is_active = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# QuerySet / Manager helpers


class TenantQuerySetMixin:
    """
    Mixin for QuerySet classes.

    Adds a single method:
        .for_tenant(tenant)  →  filters the queryset to only that tenant's rows.

    Usage — mix into any custom QuerySet:
        class ProductQuerySet(TenantQuerySetMixin, models.QuerySet):
            pass
    """
    def for_tenant(self, tenant):
        return self.filter(tenant=tenant)


class TenantQuerySet(TenantQuerySetMixin, models.QuerySet):
    """
    A ready-to-use QuerySet that already has .for_tenant().
    Referenced by TenantManager below.
    """
    pass


class TenantManager(models.Manager):
    """
    Drop-in replacement for models.Manager on any tenant-aware model.

    Gives you two ways to filter by tenant:
        Product.objects.for_tenant(tenant)          # via manager
        Product.objects.all().for_tenant(tenant)    # via queryset chain
    """
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant):
        return self.get_queryset().for_tenant(tenant)


class TenantMember(models.Model):
    """
    Links an employee to a Tenant with a role.
    The store owner is tracked via Tenant.owner (OneToOneField).
    TenantMember is for everyone else who works in the store.

    Roles:
      manager — full store access (same as owner, but cannot delete the store)
      staff   — manage inventory, view/update orders
      viewer  — read-only access
    """
    ROLE_MANAGER = 'manager'
    ROLE_STAFF   = 'staff'
    ROLE_VIEWER  = 'viewer'
    ROLE_CHOICES = [
        (ROLE_MANAGER, 'Manager'),
        (ROLE_STAFF,   'Staff'),
        (ROLE_VIEWER,  'Viewer'),
    ]

    tenant    = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='members')
    user      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant_memberships',
    )
    role      = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STAFF)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('tenant', 'user')]
        ordering = ['tenant', 'role']

    def __str__(self):
        return f'{self.user.username} @ {self.tenant.name} ({self.role})'
