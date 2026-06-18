# Multi-Tenant Architecture

This document explains how the multi-vendor (multi-tenant) system works in this project — why each decision was made and how it all fits together, with real examples.

---

## What Is Multi-Tenancy?

Imagine three different shops — **ShopA**, **ShopB**, and **ShopC** — all running on the same backend. Each shop has its own products, warehouses, orders, and coupons. They must **never see each other's data**, even though they all share a single database.

That is exactly what this system does.

```
Single Database
│
├── ShopA (Tenant)
│   ├── Products: iPhone 15, MacBook
│   ├── Warehouses: Kathmandu HQ, Pokhara Branch
│   └── Orders: #101, #102
│
├── ShopB (Tenant)
│   ├── Products: Nike Shoes, Adidas Cap
│   ├── Warehouses: Lalitpur Store
│   └── Orders: #201, #202
│
└── ShopC (Tenant)
    ├── Products: Rice 5kg, Mustard Oil
    └── Orders: #301
```

Every record in the database has a `tenant_id` column. When ShopA's admin logs in, they only ever see rows where `tenant_id = ShopA`.

---

## The Tenant Model

**File:** `tenants/models.py`

```python
class Tenant(models.Model):
    name       = models.CharField(max_length=255, unique=True)
    slug       = models.SlugField(max_length=100, unique=True)
    description= models.TextField(blank=True)
    owner      = models.OneToOneField(CustomUser, ...)
    is_active  = models.BooleanField(default=True)
```

### Why each field?

| Field | Why |
|---|---|
| `name` | Human-readable store name — "ShopA Electronics" |
| `slug` | URL-safe identifier used in the `X-Tenant-Slug` header — `"shopa-electronics"` |
| `owner` | The vendor admin who owns this store. `OneToOneField` means one user = one store |
| `is_active` | Lets platform admins disable a vendor without deleting their data |

### Example

```json
{
  "id": 1,
  "name": "ShopA Electronics",
  "slug": "shopa-electronics",
  "owner": 5,
  "is_active": true
}
```

---

## TenantQuerySetMixin

**File:** `tenants/models.py`

```python
class TenantQuerySetMixin:
    def for_tenant(self, tenant):
        return self.filter(tenant=tenant)
```

### Why a mixin instead of putting `.filter()` everywhere?

Without this mixin, every view would need to write:
```python
# BAD — repeated everywhere, easy to forget
Product.objects.filter(tenant=tenant)
Order.objects.filter(tenant=tenant)
Coupon.objects.filter(tenant=tenant)
```

With the mixin, you write it **once** and reuse it everywhere:
```python
# GOOD — clean, consistent, impossible to forget
Product.objects.for_tenant(tenant)
Order.objects.for_tenant(tenant)
Coupon.objects.for_tenant(tenant)
```

A mixin is just a class you "mix into" another class to add extra methods. Think of it like adding a superpower to any QuerySet.

### TenantQuerySet and TenantManager

```python
class TenantQuerySet(TenantQuerySetMixin, models.QuerySet):
    pass

class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant):
        return self.get_queryset().for_tenant(tenant)
```

- **TenantQuerySet** = a QuerySet that has `.for_tenant()` on it
- **TenantManager** = tells Django to use `TenantQuerySet` for all `.objects` calls

Every tenant-aware model sets:
```python
objects = TenantManager()
```

This means you can chain it naturally:
```python
# All work the same way:
Product.objects.for_tenant(shopa)
Product.objects.for_tenant(shopa).filter(category='Electronics')
Product.objects.all().for_tenant(shopa).order_by('-created_at')
```

---

## How the Tenant FK Is Added to Models

Every business model now has this field:

```python
tenant = models.ForeignKey(
    'tenants.Tenant',
    on_delete=models.CASCADE,
    related_name='products',   # (varies per model)
    null=True,
    blank=True,
)
```

### Why `null=True, blank=True`?

Because the database already has existing rows with no `tenant_id`. Making the field required would instantly break the database on migration. By allowing null, existing data survives and you can backfill tenant assignments later via the Django admin.

### Models that got a tenant FK

| Model | App | Why it needs tenant isolation |
|---|---|---|
| `Product` | products | Each vendor sells their own products |
| `Warehouse` | warehouses | Each vendor owns their own warehouses |
| `Inventory` | inventory | Stock levels are per-vendor |
| `Order` | orders | Orders are placed with a specific vendor |
| `Coupon` | coupons | Discount codes are vendor-specific |
| `Review` | reviews | Reviews are on products that belong to a vendor |
| `Notification` | notifications | Notifications are tied to orders (which are per-vendor) |

### Models that do NOT have a tenant FK

| Model | Why |
|---|---|
| `CustomUser` | Users are global — a customer can shop from any vendor |
| `Profile` | Belongs to a user, not a vendor |
| `Wishlist` | Belongs to a user globally (indirectly filtered via product) |

---

## Unique Constraints Per Tenant

Before multi-tenancy, some fields were globally unique:

```python
sku = models.CharField(unique=True)   # Product
name = models.CharField(unique=True)  # Warehouse
code = models.CharField(unique=True)  # Coupon
```

This would prevent two different vendors from having a product with SKU `"SHOE-001"` — clearly wrong. The fix: make uniqueness **per tenant**.

```python
# Product
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['tenant', 'sku'],
            name='unique_tenant_sku'
        )
    ]
```

Now ShopA and ShopB can both have SKU `"SHOE-001"` — they just can't have two products with the same SKU **within their own store**.

Same pattern for:
- `Warehouse`: `(tenant, name)` is unique — two vendors can have a warehouse named "Main Branch"
- `Coupon`: `(tenant, code)` is unique — two vendors can both have a coupon `"SAVE10"`
- `Inventory`: `(tenant, product, warehouse)` is unique — one stock record per product per warehouse per vendor

---

## TenantMiddleware

**File:** `tenants/middleware.py`

```python
class TenantMiddleware:
    def __call__(self, request):
        request.tenant = SimpleLazyObject(lambda: _resolve_tenant(request))
        return self.get_response(request)
```

### What does middleware do?

Middleware runs on **every single request**, before it reaches any view. This middleware's only job is to figure out which tenant this request belongs to and attach it to `request.tenant`.

### How does it identify the tenant?

Priority order:

1. **`X-Tenant-Slug` header** — frontend or app sends the vendor's slug
2. **`?tenant=` query param** — handy for browser testing
3. **Logged-in user's owned tenant** — if the user is a vendor admin

```python
def _resolve_tenant(request):
    slug = request.headers.get('X-Tenant-Slug') or request.GET.get('tenant')
    if slug:
        return Tenant.objects.get(slug=slug, is_active=True)

    if request.user.is_authenticated:
        try:
            return request.user.owned_tenant  # vendor admin
        except Tenant.DoesNotExist:
            pass

    return None  # platform admin or unauthenticated customer
```

### Example request from a mobile app

```http
GET /api/products/
Authorization: Bearer eyJ...
X-Tenant-Slug: shopa-electronics
```

Django receives this → middleware sets `request.tenant = <ShopA Tenant>` → the view filters products by ShopA.

### `SimpleLazyObject` — why?

```python
request.tenant = SimpleLazyObject(lambda: _resolve_tenant(request))
```

Without lazy evaluation, `_resolve_tenant()` would hit the database on every request, even endpoints that don't need tenant context (like `/admin/` or `/swagger/`). `SimpleLazyObject` means the database query only runs the first time `request.tenant` is actually accessed. If it's never accessed, no query runs.

---

## TenantViewMixin

**File:** `tenants/mixins.py`

```python
class TenantViewMixin:
    def get_tenant(self):
        tenant = getattr(self.request, 'tenant', None)
        if tenant is None:
            raise PermissionDenied('Tenant could not be identified.')
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
```

### How to use it in a ViewSet

```python
from tenants.mixins import TenantViewMixin

class ProductViewSet(TenantViewMixin, viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedCustomer]
```

That is all you need. The mixin handles the rest:

- `get_queryset()` — automatically adds `.filter(tenant=...)` to every list/detail/update/delete
- `perform_create()` — automatically stamps `tenant=...` on every new object
- `get_tenant()` — raises `403 Forbidden` if no tenant is identified

### Example: what happens when ShopA admin creates a product

```
POST /api/products/
X-Tenant-Slug: shopa-electronics
{ "name": "iPhone 15", "sku": "IP15-BLK", "price": 145000 }

→ middleware sets request.tenant = ShopA
→ ProductViewSet.perform_create() calls serializer.save(tenant=ShopA)
→ Product row is inserted with tenant_id = 1 (ShopA's id)
```

ShopB admin cannot see this product because their requests have `tenant_id = 2`.

---

## Tenant API Endpoints

**Base URL:** `/api/tenants/`

| Method | Endpoint | Who | What |
|---|---|---|---|
| GET | `/api/tenants/` | Platform Admin | List all vendors |
| POST | `/api/tenants/` | Platform Admin | Register a new vendor |
| GET | `/api/tenants/{id}/` | Platform Admin | View a vendor |
| PUT | `/api/tenants/{id}/` | Platform Admin | Update a vendor |
| DELETE | `/api/tenants/{id}/` | Platform Admin | Remove a vendor |
| GET | `/api/tenants/me/` | Vendor Admin | View your own store |

### Register a vendor (platform admin)

```http
POST /api/tenants/
Authorization: Bearer <platform-admin-token>
Content-Type: application/json

{
  "name": "ShopA Electronics",
  "slug": "shopa-electronics",
  "description": "Best electronics in Kathmandu",
  "owner": 5
}
```

Response:
```json
{
  "id": 1,
  "name": "ShopA Electronics",
  "slug": "shopa-electronics",
  "owner": 5,
  "owner_username": "shopa_admin",
  "owner_email": "admin@shopa.com",
  "is_active": true,
  "created_at": "2026-06-17T10:00:00Z"
}
```

---

## How It All Works Together — Full Flow

### Step 1: Platform admin creates a vendor

```
POST /api/tenants/  { name: "ShopA", slug: "shopa", owner: 5 }
→ Tenant created with id=1
→ User #5 becomes ShopA's vendor admin
```

### Step 2: Vendor admin adds a product

```
POST /api/products/
X-Tenant-Slug: shopa
Authorization: Bearer <vendor-admin-token>
{ "name": "iPhone 15", "sku": "IP15", "price": 145000 }

→ Middleware: request.tenant = ShopA (id=1)
→ ProductViewSet.perform_create(): saves with tenant_id=1
→ DB row: { id:1, tenant_id:1, name:"iPhone 15", sku:"IP15", price:145000 }
```

### Step 3: Customer browses ShopA's products

```
GET /api/products/
X-Tenant-Slug: shopa

→ Middleware: request.tenant = ShopA
→ ProductViewSet.get_queryset(): Product.objects.filter(tenant=ShopA)
→ Returns only ShopA's products. ShopB's products are invisible.
```

### Step 4: Customer places an order

```
POST /api/orders/
X-Tenant-Slug: shopa
Authorization: Bearer <customer-token>
{ "customer_name": "Ram", "payment_method": "esewa", "items": [...] }

→ Order saved with tenant_id=1
→ Only ShopA's inventory is deducted
→ ShopB's inventory untouched
```

---

## Running Migrations

After pulling this code, run:

```bash
python manage.py makemigrations tenants
python manage.py makemigrations products warehouses inventory orders coupons reviews notifications
python manage.py migrate
```

---

## Summary

| Piece | File | Job |
|---|---|---|
| `Tenant` model | `tenants/models.py` | Represents one vendor store |
| `TenantQuerySetMixin` | `tenants/models.py` | Adds `.for_tenant()` to any QuerySet |
| `TenantManager` | `tenants/models.py` | Wires `TenantQuerySet` into `Model.objects` |
| `TenantMiddleware` | `tenants/middleware.py` | Sets `request.tenant` on every request |
| `TenantViewMixin` | `tenants/mixins.py` | Auto-scopes views to the current tenant |
| `tenant FK` | every business model | The actual database column that isolates data |
| `unique_together` | Product, Warehouse, Coupon, Inventory | Allows same names/codes across different vendors |
