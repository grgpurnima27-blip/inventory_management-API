# Inventory Management API

A production-ready **multi-vendor** backend REST API for managing product inventory, multi-warehouse stock, orders, payments, and analytics — built with Django and Django REST Framework.

Each vendor operates in a fully isolated store (tenant). Customers can shop across stores. Platform admins manage the vendors.

Live API: [Railway deployment](https://inventory-management-api-production.up.railway.app)  
Interactive Docs: `/swagger/` · `/redoc/`

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Multi-Vendor Architecture](#multi-vendor-architecture)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [How to Use the API](#how-to-use-the-api)
- [API Reference](#api-reference)
  - [Authentication](#authentication-apiauthentication)
  - [Tenants](#tenants-apitenants)
  - [Team Members](#team-members-apitenant-members)
  - [Products](#products-apiproducts)
  - [Warehouses](#warehouses-apiwarehouses)
  - [Inventory](#inventory-apiinventory)
  - [Orders](#orders-apiorders)
  - [Coupons](#coupons-apicoupons)
  - [Reviews](#reviews-apireviews)
  - [Wishlist](#wishlist-apiwishlist)
  - [Notifications](#notifications-apinotifications)
  - [Reports](#reports-apireports)
- [Role-Based Access Control](#role-based-access-control)
- [Payment Integrations](#payment-integrations)
- [Google Sign-In](#google-sign-in-setup)
- [Deployment](#deployment)

---

## Features

- **Multi-Vendor / Multi-Tenant** — Shared database with full per-tenant data isolation via `X-Tenant-Slug` header
- **JWT Authentication** — SimpleJWT with token blacklist on logout; separate login flows per user type
- **Google OAuth 2.0** — Sign in with Google; auto-creates customer accounts
- **Role-Based Access Control** — Platform admin, vendor admin, employee (manager/staff/viewer), customer
- **Team Management** — Store owners can add/remove employees with role-based store access
- **Multi-Warehouse Inventory** — Stock auto-routed to warehouse nearest the delivery city
- **Atomic Transactions** — Inventory deducted and restored inside `@transaction.atomic` blocks
- **eSewa & Khalti Payments** — QR code generation for eSewa; transaction ID verification for both
- **Coupon System** — Per-tenant percentage and fixed-amount discount codes with usage limits and expiry
- **Order Lifecycle** — Full tracking: `pending → processing → shipped → completed` with auto notifications
- **Profile Avatars** — Auto-generated from user initials on registration (UI Avatars)
- **Cloudinary Media Storage** — Product images and user avatars stored in the cloud
- **Admin Analytics** — Cached reports: top products, revenue by city, sales charts, coupon usage
- **Interactive API Docs** — Swagger UI and Redoc via `drf-spectacular` with built-in auth support

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6.0.5 + Django REST Framework 3.17.1 |
| Authentication | SimpleJWT 5.5.1 + social-auth-app-django 5.9.0 |
| Database | SQLite (dev) / PostgreSQL via Neon (production) |
| Media Storage | Cloudinary |
| API Docs | drf-spectacular 0.29.0 + Swagger UI / Redoc |
| Server | Gunicorn 26.0.0 + WhiteNoise |
| Payments | eSewa, Khalti (django-esewa 1.1.0) |
| Caching | Django LocMemCache (60s TTL on reports) |
| Deployment | Railway.app + Neon PostgreSQL |

---

## Multi-Vendor Architecture

The platform uses a **shared database, tenant-isolated** approach. Every business model (Product, Warehouse, Inventory, Order, Coupon, Review) carries a `tenant` foreign key. The `TenantMiddleware` resolves the current tenant from the `X-Tenant-Slug` request header and scopes all queries automatically.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client / Frontend                        │
│              Authorization: Bearer <token>                      │
│              X-Tenant-Slug: techmart          ← store header   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────────────┐
│                   TenantMiddleware                               │
│   Resolves tenant from X-Tenant-Slug → stamps request.tenant   │
├─────────────────────────────────────────────────────────────────┤
│                  Django REST Framework API                       │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ tenants  │  │ accounts │  │products │  │   warehouses    │ │
│  └──────────┘  └──────────┘  └─────────┘  └─────────────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │inventory │  │  orders  │  │coupons  │  │    reviews      │ │
│  └──────────┘  └──────────┘  └─────────┘  └─────────────────┘ │
│  ┌──────────┐  ┌─────────────────────────────────────────────┐ │
│  │ wishlist │  │            notifications                    │ │
│  └──────────┘  └─────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────▼──────┐           ┌──────▼──────┐
       │  Neon PgSQL │           │  Cloudinary │
       │  (all data) │           │   (media)   │
       └─────────────┘           └─────────────┘
```

**Entity Relationships**

```
Tenant ──< Product ──< Inventory >── Warehouse
  │            │
  │            └──< Review
  │            └──< Wishlist
  │
  ├──< Order ──< OrderItem >── Product
  │       └──< Notification
  │
  ├──< Coupon
  ├──< TenantMember >── CustomUser
  └── owner (CustomUser)

CustomUser ── Profile
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- pip
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/grgpurnima27/inventory-management-API.git
cd inventory-management-API

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Apply database migrations
python manage.py migrate

# Seed a test vendor with full data for Swagger testing
python manage.py seed_tenant

# (Optional) Create a platform superadmin
python manage.py createsuperuser
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True

# Cloudinary (media storage)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# PostgreSQL (production — Neon or any Postgres provider)
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# Optional: Pexels API (auto-fetch product images)
PEXELS_API_KEY=your-pexels-api-key
```

---

## How to Use the API

Every store request needs **two headers**:

| Header | Value | Required for |
|---|---|---|
| `Authorization` | `Bearer <access_token>` | All authenticated endpoints |
| `X-Tenant-Slug` | e.g. `techmart` | All store endpoints (products, orders, etc.) |

### Step 1 — Login

Use the right login endpoint for your user type:

| User type | Endpoint | Body |
|---|---|---|
| New vendor | `POST /api/auth/vendor/register/` | `username`, `password`, `email`, `store_name`, `store_slug` |
| Customer | `POST /api/auth/login/` | `username`, `password` |
| Store owner | `POST /api/auth/vendor/login/` | `username`, `password` (only works after admin approval) |
| Employee | `POST /api/auth/employee/login/` | `username`, `password`, `tenant_slug` |
| Platform admin | `POST /api/auth/admin/login/` | `username`, `password` |

The login response always tells you the `tenant_slug` to use:

```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "user": { "username": "techmart_admin", "role": "admin" },
  "store": {
    "slug": "techmart",
    "name": "TechMart Nepal",
    "your_role": "owner"
  },
  "next_step": "Set header  X-Tenant-Slug: techmart  on all store requests."
}
```

### Step 2 — Authorize in Swagger

1. Open `/swagger/`
2. Click **Authorize** (top right)
3. Fill in **both** fields:
   - `jwtAuth` → paste your `access` token (no `Bearer ` prefix needed)
   - `tenantAuth` → paste the `slug` from the login response (e.g. `techmart`)
4. Click **Authorize** → every request now sends both headers automatically

### Step 3 — Make requests

All store endpoints (`/api/products/`, `/api/orders/`, etc.) automatically scope to the tenant from the `X-Tenant-Slug` header. You will only see and create data belonging to that store.

---

## API Reference

### Authentication (`/api/auth/`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/register/` | Public | Register a new customer account |
| POST | `/login/` | Public | Customer login — returns JWT |
| POST | `/vendor/register/` | Public | Vendor self-registration — creates account + store (pending approval) |
| POST | `/vendor/login/` | Public | Store owner login — returns JWT + tenant info (only works after approval) |
| POST | `/employee/login/` | Public | Employee login — requires `tenant_slug` in body |
| POST | `/admin/login/` | Public | Platform admin login |
| POST | `/token/refresh/` | Public | Refresh an expired access token |
| GET | `/me/` | Auth | Get current user's info |
| POST | `/change-password/` | Auth | Update password |
| POST | `/logout/` | Auth | Blacklist refresh token |
| POST | `/google/login` | Public | Sign in with a Google access token |
| POST | `/forgot-password/` | Public | Request password reset |
| POST | `/reset-password/{token}/` | Public | Reset password via token |

**Vendor Login**
```http
POST /api/auth/vendor/login/
Content-Type: application/json

{
  "username": "techmart_admin",
  "password": "Admin@1234"
}
```

**Employee Login**
```http
POST /api/auth/employee/login/
Content-Type: application/json

{
  "username": "john_staff",
  "password": "Staff@1234",
  "tenant_slug": "techmart"
}
```

---

### Tenants (`/api/tenants/`)

Platform admin only (except `/me/`).

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Platform admin | List all stores — use `?is_active=false` for pending |
| POST | `/` | Platform admin | Manually create a vendor store |
| GET | `/{id}/` | Platform admin | Get store details |
| PUT/PATCH | `/{id}/` | Platform admin | Update store info |
| DELETE | `/{id}/` | Platform admin | Delete a store |
| POST | `/{id}/approve/` | Platform admin | Approve a pending vendor registration |
| POST | `/{id}/reject/` | Platform admin | Reject and delete a pending registration |
| GET | `/me/` | Auth | Get the store owned by the logged-in vendor |

**Vendor approval workflow:**

```
1. Vendor submits:  POST /api/auth/vendor/register/
                    → store created with is_active=false

2. Admin reviews:   GET /api/tenants/?is_active=false
                    → lists all pending stores with owner info

3a. Approve:        POST /api/tenants/{id}/approve/
                    → store goes live, vendor can now login

3b. Reject:         POST /api/tenants/{id}/reject/
                    → store deleted, vendor account kept (can re-apply)
```

**Create Store**
```http
POST /api/tenants/
Authorization: Bearer <platform_admin_token>
Content-Type: application/json

{
  "name": "TechMart Nepal",
  "slug": "techmart",
  "description": "Best electronics store in Nepal.",
  "owner": 1,
  "is_active": true
}
```

---

### Team Members (`/api/tenant-members/`)

Store owner only. Requires `X-Tenant-Slug` header.

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Owner | List all members of your store |
| POST | `/` | Owner | Add a user as a store member |
| PATCH | `/{id}/` | Owner | Update a member's role |
| DELETE | `/{id}/` | Owner | Remove a member from the store |

**Add a member**
```http
POST /api/tenant-members/
Authorization: Bearer <owner_token>
X-Tenant-Slug: techmart
Content-Type: application/json

{
  "add_user": "john_doe",
  "role": "staff"
}
```

**Member roles:**

| Role | Access |
|---|---|
| `manager` | Full store access — products, warehouses, inventory, coupons, orders |
| `staff` | Manage inventory, view and update orders |
| `viewer` | Read-only access to store data |

---

### Products (`/api/products/`)

Requires `X-Tenant-Slug` header.

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Public | List all products in the store |
| POST | `/` | Vendor admin / Manager / Staff | Create a product |
| GET | `/{id}/` | Public | Get a single product |
| PUT/PATCH | `/{id}/` | Vendor admin / Manager / Staff | Update a product |
| DELETE | `/{id}/` | Vendor admin / Manager / Staff | Delete a product |
| POST | `/{id}/upload-image/` | Vendor admin / Manager / Staff | Upload product image to Cloudinary |
| POST | `/{id}/fetch-image/` | Vendor admin / Manager / Staff | Auto-fetch image from Pexels → Cloudinary |

**Query parameters:** `?search=laptop`, `?ordering=price`, `?ordering=-created_at`

---

### Warehouses (`/api/warehouses/`)

Requires `X-Tenant-Slug` header.

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Public | List warehouses in the store |
| POST | `/` | Vendor admin / Manager / Staff | Create a warehouse |
| GET | `/{id}/` | Public | Get a warehouse |
| PUT/PATCH | `/{id}/` | Vendor admin / Manager / Staff | Update a warehouse |
| DELETE | `/{id}/` | Vendor admin / Manager / Staff | Delete a warehouse |

---

### Inventory (`/api/inventory/`)

Requires `X-Tenant-Slug` header. Vendor admin / Manager / Staff only.

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Vendor admin+ | List all stock records |
| POST | `/` | Vendor admin+ | Allocate stock to a warehouse |
| GET | `/{id}/` | Vendor admin+ | Get a stock record |
| PUT/PATCH | `/{id}/` | Vendor admin+ | Adjust stock quantity |
| DELETE | `/{id}/` | Vendor admin+ | Remove a stock record |

**Query parameters:** `?product=1`, `?warehouse=2`, `?low_stock=true`

---

### Orders (`/api/orders/`)

Requires `X-Tenant-Slug` header.

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Auth | List orders (customers: own only; admin: all) |
| POST | `/` | Auth | Place a new order |
| GET | `/{id}/` | Owner / Admin | Full order details |
| PUT/PATCH | `/{id}/` | Vendor admin+ | Update order or payment status |
| DELETE | `/{id}/` | Vendor admin+ | Delete an order |
| POST | `/{id}/cancel/` | Owner / Vendor admin+ | Cancel and restore inventory |
| GET | `/{id}/track/` | Auth | Order status timeline |
| POST | `/{id}/confirm-payment/` | Auth | Confirm eSewa / Khalti payment |

**Create Order**
```http
POST /api/orders/
Authorization: Bearer <token>
X-Tenant-Slug: techmart
Content-Type: application/json

{
  "customer_name": "John Doe",
  "delivery_city": "Kathmandu",
  "payment_method": "esewa",
  "coupon_code": "SAVE10",
  "items": [
    { "product": 1, "quantity": 2 },
    { "product": 3, "quantity": 1 }
  ]
}
```

> `delivery_city` is optional if the customer's profile already has a city set.

**Order status flow**
```
pending → processing → shipped → completed
    └───────────────────────────→ cancelled
```

---

### Coupons (`/api/coupons/`)

Requires `X-Tenant-Slug` header. Coupons are fully isolated per tenant.

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Vendor admin+ | List store coupons |
| POST | `/` | Vendor admin+ | Create a coupon |
| GET | `/{id}/` | Vendor admin+ | Get a coupon |
| PUT/PATCH | `/{id}/` | Vendor admin+ | Update a coupon |
| DELETE | `/{id}/` | Vendor admin+ | Delete a coupon |
| POST | `/apply/` | Auth | Validate a coupon and calculate discount |

**Apply Coupon**
```http
POST /api/coupons/apply/
Authorization: Bearer <token>
X-Tenant-Slug: techmart
Content-Type: application/json

{
  "code": "SAVE10",
  "order_amount": "5000.00"
}
```

---

### Reviews (`/api/reviews/`)

Requires `X-Tenant-Slug` header. One review per customer per product. Only purchasers can review.

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Public | List all reviews (`?product=1` to filter) |
| POST | `/` | Auth | Submit a review (must have purchased) |
| GET | `/{id}/` | Public | Get a single review |
| PATCH | `/{id}/` | Owner | Update your review |
| DELETE | `/{id}/` | Owner / Vendor admin+ | Delete a review |

---

### Wishlist (`/api/wishlist/`)

Requires `X-Tenant-Slug` header. Scoped to both user and the current store.

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Auth | Get current user's wishlist |
| POST | `/` | Auth | Add a product |
| DELETE | `/{id}/` | Auth | Remove a product |
| DELETE | `/clear/` | Auth | Clear the entire wishlist |

---

### Notifications (`/api/notifications/`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Auth | List all notifications |
| GET | `/unread-count/` | Auth | Count of unread notifications |
| POST | `/mark-all-read/` | Auth | Mark all as read (scoped to current tenant) |
| PATCH | `/{id}/read/` | Auth | Mark a single notification as read |
| DELETE | `/{id}/` | Auth | Delete a notification |

---

### Reports (`/api/reports/`)

Admin-only, cached 60 seconds. Requires `X-Tenant-Slug` header.

| Endpoint | Query params | Description |
|---|---|---|
| `/inventory-summary/` | — | Product count, total stock, low-stock alerts |
| `/top-products/` | `?days=30` | Top 10 products by quantity sold and revenue |
| `/revenue-by-city/` | `?days=30` | Revenue breakdown by delivery city |
| `/top-customers/` | `?days=30` | Top 10 customers by total spend |
| `/sales-chart/` | `?period=daily&days=30` | Time-series sales data |
| `/coupon-usage/` | — | All coupons with usage stats |

---

## Role-Based Access Control

### Platform-level roles

| Role | How to create | Can do |
|---|---|---|
| **Platform admin** | `python manage.py createsuperuser` (`is_staff=True`) | Create/manage Tenants only |
| **Vendor admin** | Register normally + assigned `owned_tenant` | Manage their store's data |
| **Customer** | `POST /api/auth/register/` | Browse, order, review, wishlist |

### Store-level roles (TenantMember)

| Role | Products | Warehouses | Inventory | Orders | Coupons | Manage team |
|---|---|---|---|---|---|---|
| `owner` | Full | Full | Full | Full | Full | Yes |
| `manager` | Full | Full | Full | Full | Full | No |
| `staff` | Full | Full | Full | View/Update | Full | No |
| `viewer` | Read | Read | Read | Read | Read | No |

### Permission classes

| Class | Description |
|---|---|
| `IsPlatformAdmin` | `is_staff=True` only — tenant management |
| `IsVendorAdmin` | Store owner or manager/staff member of the current tenant |
| `IsTenantOwner` | Only the tenant's owner — team management |
| `IsAdminOrReadOnly` | Public GET; write requires admin |
| `IsAuthenticatedCustomer` | Any logged-in user |
| `IsOwnerOrAdmin` | Object-level: owner or admin |

---

## Payment Integrations

### eSewa

1. Create order with `"payment_method": "esewa"`
2. Response includes a base64-encoded QR code (`esewa://payment?...`)
3. Customer scans and pays via eSewa app
4. Submit transaction ID: `POST /api/orders/{id}/confirm-payment/`
5. API marks payment `paid`, order advances to `processing`

### Khalti

Same flow — create order with `"payment_method": "khalti"`, confirm with transaction ID.

### Cash on Delivery

No confirmation needed. Payment stays `pending` until admin marks it `paid`.

---

## Google Sign-In Setup

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
3. Application type: **Web application**
4. Authorized redirect URIs:
   ```
   http://localhost:8000/api/auth/google/callback/
   https://your-railway-domain.up.railway.app/api/auth/google/callback/
   ```
5. Copy Client ID and Client Secret to `.env`

### 2. Token Flow (mobile / SPA)

```http
POST /api/auth/google/login
Content-Type: application/json

{ "access_token": "<google-access-token>" }
```

Returns the same JWT response as regular login. New users are auto-created with `role=customer`.

---

## Deployment

Deployed on **Railway.app** with **Neon PostgreSQL**.

**`railway.json`**
```json
{
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "python manage.py collectstatic --noinput"
  },
  "deploy": {
    "startCommand": "python manage.py migrate --no-input && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Required Railway environment variables:**

| Variable | Description |
|---|---|
| `DATABASE_URL` | Neon PostgreSQL connection string (with `?sslmode=require`) |
| `DJANGO_SECRET_KEY` | Django secret key |
| `DEBUG` | Set to `False` in production |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary credentials |
| `CLOUDINARY_API_KEY` | Cloudinary credentials |
| `CLOUDINARY_API_SECRET` | Cloudinary credentials |
| `GOOGLE_CLIENT_ID` | Google OAuth credentials |
| `GOOGLE_CLIENT_SECRET` | Google OAuth credentials |

**After first deploy — seed test data:**
```bash
railway run python manage.py seed_tenant
railway run python manage.py createsuperuser
```

---

## Seeded Test Credentials

Run `python manage.py seed_tenant` to create:

| Role | Username | Password |
|---|---|---|
| Vendor admin (owner) | `techmart_admin` | `Admin@1234` |
| Customer | `test_customer` | `Customer@1234` |

Tenant slug: **`techmart`**

Use `techmart_admin` / `Admin@1234` with `POST /api/auth/vendor/login/` and paste `techmart` in the Swagger `tenantAuth` field.

---

## API Documentation

| URL | Description |
|---|---|
| `/swagger/` | Swagger UI — interactive console with auth support |
| `/redoc/` | Redoc formatted documentation |
| `/api/schema/` | Raw OpenAPI 3.0 JSON schema |

---

## License

MIT
