# Inventory Management API

A production-ready backend REST API for managing product inventory, multi-warehouse stock, orders, payments, and analytics — built with Django and Django REST Framework.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running the Server](#running-the-server)
- [API Reference](#api-reference)
  - [Authentication](#authentication-apiauthentication)
  - [Products](#products-apiproducts)
  - [Warehouses](#warehouses-apiwarehouses)
  - [Inventory](#inventory-apiinventory)
  - [Orders](#orders-apiorders)
  - [Reviews](#reviews-apireviews)
  - [Wishlist](#wishlist-apiwishlist)
  - [Coupons](#coupons-apicoupons)
  - [Notifications](#notifications-apinotifications)
  - [Reports](#reports-apireports)
- [Payment Integrations](#payment-integrations)
- [Role-Based Access Control](#role-based-access-control)
- [Deployment](#deployment)
- [API Documentation](#api-documentation)

---

## Features

- **JWT Authentication** — SimpleJWT with token blacklist on logout; 7-day access / 30-day refresh
- **Google OAuth 2.0** — Sign in with Google; auto-creates user accounts
- **Role-Based Access Control** — `admin` and `customer` roles with fine-grained permissions
- **Multi-Warehouse Inventory** — Stock auto-routed to the warehouse nearest the delivery city
- **Atomic Transactions** — Inventory deducted and restored within `@transaction.atomic` blocks
- **eSewa & Khalti Payments** — QR code generation for eSewa; transaction ID verification for both
- **Coupon System** — Percentage and fixed-amount discount codes with usage limits and expiry
- **Order Lifecycle** — Full tracking from `pending` → `processing` → `shipped` → `completed` with notifications
- **Real-Time Notifications** — Auto-generated per order event; unread count endpoint
- **Admin Analytics** — Cached reports: top products, revenue by city, sales charts, coupon usage
- **Cloudinary Media Storage** — Product images and user avatars stored in the cloud
- **Interactive API Docs** — Swagger UI and Redoc via `drf-spectacular`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6.0.5 + Django REST Framework 3.17.1 |
| Authentication | SimpleJWT 5.5.1 + social-auth-app-django 5.9.0 |
| Database | SQLite (dev) / PostgreSQL (production) |
| Media Storage | Cloudinary |
| API Docs | drf-spectacular 0.29.0 + Swagger/Redoc |
| Server | Gunicorn 26.0.0 |
| Payments | eSewa, Khalti (django-esewa 1.1.0) |
| Caching | Django LocMemCache (60s TTL on reports) |
| Deployment | Railway.app |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Client / Frontend                    │
└───────────────────────┬──────────────────────────────────┘
                        │ HTTPS
┌───────────────────────▼──────────────────────────────────┐
│              Django REST Framework API                   │
│                                                          │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐  │
│  │accounts │  │ products │  │ orders  │  │ reports  │  │
│  └─────────┘  └──────────┘  └─────────┘  └──────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │inventory │  │warehouses│  │  coupons │  │reviews │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
│  ┌──────────┐  ┌──────────────────────────────────────┐  │
│  │ wishlist │  │           notifications              │  │
│  └──────────┘  └──────────────────────────────────────┘  │
└───────────────┬──────────────────────────────────────────┘
                │
    ┌───────────┴───────────┐
    │                       │
┌───▼────┐           ┌──────▼──────┐
│SQLite  │           │  Cloudinary │
│/ PgSQL │           │  (Media)    │
└────────┘           └─────────────┘
```

**Entity Relationships**

```
CustomUser ──< Order ──< OrderItem >── Product >── Inventory >── Warehouse
    │                                     │
    ├──< Review                           └── Wishlist
    ├──< Notification
    └── Profile
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
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Apply database migrations
python manage.py migrate

# Create a superuser (admin)
python manage.py createsuperuser
```

### Environment Variables

Create a `.env` file in the project root:

```env
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True

# Cloudinary (media storage)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Email (Gmail SMTP)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Frontend URL (used in email links)
FRONTEND_URL=http://localhost:3000

# PostgreSQL (production only)
DATABASE_URL=postgresql://user:password@host:port/dbname

# Railway (production only)
RAILWAY_PUBLIC_DOMAIN=your-app.railway.app

# Optional: Pexels API (product image seeding)
PEXELS_API_KEY=your-pexels-api-key
```

### Running the Server

```bash
python manage.py runserver
```

API is available at `http://localhost:8000/api/`
Swagger UI at `http://localhost:8000/swagger/`

---

## API Reference

All authenticated endpoints require the `Authorization: Bearer <access_token>` header.

### Authentication (`/api/auth/`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/register/` | Public | Register a new customer account |
| POST | `/login/` | Public | Login and receive JWT tokens |
| POST | `/admin/login/` | Public | Admin-only login |
| POST | `/token/refresh/` | Public | Refresh an expired access token |
| POST | `/forgot-password/` | Public | Request a password reset email |
| POST | `/reset-password/{token}/` | Public | Reset password using email token |
| GET | `/me/` | Auth | Get the current user's profile |
| POST | `/change-password/` | Auth | Update password |
| POST | `/logout/` | Auth | Blacklist the refresh token |
| POST | `/google/login` | Public | Sign in with a Google access token |
| GET | `/google/auth-url` | Public | Get the Google OAuth redirect URL |

**Register**
```http
POST /api/auth/register/
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePass123"
}
```

**Login response**
```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "role": "customer"
  }
}
```

---

### Products (`/api/products/`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Public | List all products (paginated) |
| POST | `/` | Admin | Create a product |
| GET | `/{id}/` | Public | Get a single product |
| PUT | `/{id}/` | Admin | Update a product |
| DELETE | `/{id}/` | Admin | Delete a product |

**Query Parameters**

| Param | Type | Description |
|---|---|---|
| `search` | string | Filter by name, category, or SKU |
| `ordering` | string | Sort by `price`, `name`, or `created_at` (prefix `-` for descending) |
| `page` | int | Pagination |

---

### Warehouses (`/api/warehouses/`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Public | List warehouses |
| POST | `/` | Admin | Create a warehouse |
| GET | `/{id}/` | Public | Get a single warehouse |
| PUT | `/{id}/` | Admin | Update a warehouse |
| DELETE | `/{id}/` | Admin | Delete a warehouse |

---

### Inventory (`/api/inventory/`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Admin | List all inventory records |
| POST | `/` | Admin | Allocate stock to a warehouse |
| GET | `/{id}/` | Admin | Get an inventory record |
| PUT | `/{id}/` | Admin | Adjust stock quantity |
| DELETE | `/{id}/` | Admin | Remove an inventory record |

---

### Orders (`/api/orders/`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Auth | List orders (customers see own; admins see all) |
| POST | `/` | Auth | Place a new order |
| GET | `/{id}/` | Owner/Admin | Get full order details |
| PUT/PATCH | `/{id}/` | Admin | Update order or payment status |
| DELETE | `/{id}/` | Admin | Delete an order |
| POST | `/{id}/cancel/` | Owner/Admin | Cancel an order and restore inventory |
| GET | `/{id}/track/` | Auth | Get order status timeline |
| POST | `/{id}/confirm-payment/` | Auth | Confirm eSewa/Khalti payment |

**Create Order**
```http
POST /api/orders/
Authorization: Bearer <token>
Content-Type: application/json

{
  "customer_name": "John Doe",
  "delivery_city": "Kathmandu",
  "payment_method": "esewa",
  "coupon_code": "SAVE10",
  "items": [
    { "product": 3, "quantity": 2 },
    { "product": 7, "quantity": 1 }
  ]
}
```

**Order Status Flow**

```
pending → processing → shipped → completed
    └──────────────────────────→ cancelled
```

**Payment Status Flow**

```
pending → paid
       → failed
       → refunded
```

**Confirm Payment**
```http
POST /api/orders/{id}/confirm-payment/
Authorization: Bearer <token>
Content-Type: application/json

{
  "transaction_id": "TXN-ABC12345"
}
```

---

### Reviews (`/api/reviews/`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Public | List all reviews |
| POST | `/` | Auth | Submit a product review |
| GET | `/{id}/` | Public | Get a single review |

One review allowed per customer per product. Rating must be 1–5.

---

### Wishlist (`/api/wishlist/`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Auth | Get current user's wishlist |
| POST | `/` | Auth | Add a product to wishlist |
| DELETE | `/{id}/` | Auth | Remove a product from wishlist |

---

### Coupons (`/api/coupons/`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Admin | List all coupons |
| POST | `/` | Admin | Create a coupon |
| GET | `/{id}/` | Admin | Get a coupon |
| PUT | `/{id}/` | Admin | Update a coupon |
| DELETE | `/{id}/` | Admin | Delete a coupon |

**Coupon fields**

| Field | Type | Description |
|---|---|---|
| `code` | string | Unique code (auto-uppercased) |
| `discount_type` | `percentage` / `fixed` | Discount type |
| `discount_value` | decimal | Amount or percentage (≤ 100 for percentage) |
| `minimum_order_amount` | decimal | Minimum cart value required |
| `max_uses` | int | Total usage limit |
| `expires_at` | datetime | Optional expiry |

---

### Notifications (`/api/notifications/`)

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Auth | List all notifications |
| GET | `/unread-count/` | Auth | Get count of unread notifications |
| POST | `/mark-all-read/` | Auth | Mark all notifications as read |
| PATCH | `/{id}/read/` | Auth | Mark a single notification as read |
| DELETE | `/{id}/` | Auth | Delete a notification |

Notifications are auto-created on order events: `order_placed`, `order_processing`, `order_shipped`, `order_completed`, `order_cancelled`.

---

### Reports (`/api/reports/`)

All report endpoints are admin-only and cached for 60 seconds.

| Endpoint | Query Params | Description |
|---|---|---|
| `/inventory-summary/` | — | Product count, total stock, low-stock alerts, order counts |
| `/top-products/` | `?days=30` | Top 10 products by quantity sold and revenue |
| `/revenue-by-city/` | `?days=30` | Revenue breakdown by delivery city |
| `/top-customers/` | `?days=30` | Top 10 customers by total order value |
| `/sales-chart/` | `?period=daily&days=30` | Time-series sales data (daily or monthly) |
| `/coupon-usage/` | — | All coupons with usage counts and active status |

---

## Payment Integrations

### eSewa

1. Customer creates an order with `"payment_method": "esewa"`
2. Response includes a base64-encoded QR code image (`esewa://payment?...`)
3. Customer scans the QR code and pays via the eSewa app
4. Customer submits the transaction ID to `POST /api/orders/{id}/confirm-payment/`
5. API verifies uniqueness of the transaction ID and marks payment as `paid`
6. Order status automatically advances to `processing`

### Khalti

Same flow as eSewa — create order with `"payment_method": "khalti"`, confirm with a transaction ID.

### Cash on Delivery (COD)

No payment confirmation required. Payment status stays `pending` until an admin manually marks it `paid`.

---

## Role-Based Access Control

| Permission | Description |
|---|---|
| `IsAdminOrReadOnly` | Public GET; POST/PUT/DELETE requires admin |
| `IsAdminRole` | All methods require admin |
| `IsAuthenticatedCustomer` | Any logged-in user |
| `IsOwnerOrAdmin` | Object-level: owner or admin only |

| Role | Default |
|---|---|
| `admin` | Full API access, reports, inventory management |
| `customer` | Place orders, reviews, wishlist, notifications |

---

## Google Sign-In Setup

The API supports two Google OAuth flows: a **redirect flow** (browser-based) and a **token flow** (mobile/SPA — send a Google access token directly).

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services → Credentials**
4. Click **Create Credentials → OAuth 2.0 Client ID**
5. Set application type to **Web application**
6. Add the following under **Authorized redirect URIs**:
   ```
   http://localhost:8000/api/auth/google/callback/      # development
   https://your-domain.com/api/auth/google/callback/   # production
   ```
7. Copy the **Client ID** and **Client Secret**

### 2. Configure Environment Variables

Add these to your `.env` file:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

### 3. Auth Flows

#### Flow A — Token Flow (Mobile / SPA)

Use this when the frontend has already obtained a Google access token (e.g., via Google Sign-In SDK).

```http
POST /api/auth/google/login
Content-Type: application/json

{
  "access_token": "<google-access-token>"
}
```

Response:

```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "user": {
    "id": 5,
    "username": "johndoe",
    "email": "john@gmail.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_new_user": true,
    "role": "customer"
  }
}
```

- If the email does not exist, a new account is created automatically with `is_email_verified = true`
- The returned JWT tokens are identical to those from the regular login endpoint

#### Flow B — Redirect Flow (Server-Side / Traditional OAuth)

1. Get the authorization URL:

```http
GET /api/auth/google/auth-url
```

Response:

```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&response_type=code&scope=email+profile"
}
```

2. Redirect the user to `auth_url`
3. Google redirects back to `/api/auth/google/callback/` with a `code` parameter
4. Exchange the code for JWT tokens (handled server-side)

### 4. Notes

- New users created via Google Sign-In are assigned the `customer` role by default
- Username is derived from the email prefix (e.g., `john` from `john@gmail.com`). If a username conflict exists, the full email is used
- Google Sign-In accounts can also use the regular `/api/auth/change-password/` endpoint after setting a password manually

---

## Deployment

This project is deployed on **Railway.app**.

**Build configuration** (`railway.json`):

```json
{
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "startCommand": "gunicorn inventory_management.wsgi --bind 0.0.0.0:$PORT",
    "releaseCommand": "python manage.py migrate && python manage.py ensure_superuser && python manage.py verify_all_users",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Python version** (`runtime.txt`): `python-3.12.10`

**Static files** are served via WhiteNoise with compressed manifest storage.

---

## API Documentation

Interactive API documentation is auto-generated via `drf-spectacular`:

| URL | Description |
|---|---|
| `/swagger/` | Swagger UI with interactive console |
| `/redoc/` | Redoc formatted documentation |
| `/api/schema/` | Raw OpenAPI 3.0 JSON schema |

All endpoints include request/response schema, authentication requirements, and example payloads.

---

## Validation Rules

| Entity | Rules |
|---|---|
| Product | Name ≥ 3 chars; price > 0; SKU must be unique |
| Warehouse | Name ≥ 3 chars, unique; city required |
| Inventory | Quantity ≥ 0; product + warehouse combination must be unique |
| Order | customer_name ≥ 3 chars; delivery_city ≥ 2 chars |
| OrderItem | Quantity > 0; sufficient stock must exist in delivery city warehouse |
| Review | Rating 1–5; one review per user per product |
| Coupon | discount_value > 0; percentage ≤ 100; code auto-uppercased |
| Transaction ID | Must be unique across all orders; required for eSewa/Khalti confirmation |

---

## License

MIT
