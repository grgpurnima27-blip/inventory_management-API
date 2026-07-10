"""
Django settings for config project.
"""

from decimal import Decimal
from pathlib import Path
import os # imports os module for operating system interfaces (environments varabiles, file paths, etc)
from datetime import timedelta # used for JWT token expiration times
from django.core.exceptions import ImproperlyConfigured # imports expection that rises when django settings are misconfigured or missing required values 

from dotenv import load_dotenv # used to load environment variables from .env file into os.environ
from corsheaders.defaults import default_headers
import dj_database_url 
import cloudinary

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("DJANGO_SECRET_KEY")

# Check if SECRET_KEY is set (critical for production)
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "The DJANGO_SECRET_KEY environment variable must not be empty. "
        "Please set it in your Railway.app environment variables."
    )

DEBUG = os.getenv("DEBUG", "False") == "True"
# True in development, but False in production, hides errors and better security 

ALLOWED_HOSTS = [
    "127.0.0.1", # local computer IP
    
    "localhost", # local computer name 
    ".railway.app", # Any subdomain of railway.app
    ".up.railway.app",  ### Add Railway default domain
    "192.168.18.227",
    "192.168.18.220",
]

railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
if railway_domain:
    ALLOWED_HOSTS.append(railway_domain)

CSRF_TRUSTED_ORIGINS = [
    "https://*.railway.app",
    "https://*.up.railway.app",
]

# CORS Settings (Updated)
# Allow all origins in development, restrict in production
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only allow all in debug mode

# If not in debug mode, specify allowed origins
if not DEBUG:
    # Read allowed origins from environment variable or use defaults
    cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if cors_origins:
        CORS_ALLOWED_ORIGINS = cors_origins.split(",")
    else:
        CORS_ALLOWED_ORIGINS = [ # development: Allow local frontends
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
            "https://*.railway.app",
            "https://*.up.railway.app",
        ]
else:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "https://*.railway.app",
        "https://*.up.railway.app",
    ]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    "x-tenant-slug"
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_ALL_HEADERS = True

# CLOUDINARY

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": os.getenv("CLOUDINARY_API_KEY"),
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),
}

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

DEFAULT_FILE_STORAGE = (
    "cloudinary_storage.storage.MediaCloudinaryStorage"
)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# Simple fix - use console backend on Railway
if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
# Frontend/Backend URL for email links
FRONTEND_URL = os.getenv(
    'FRONTEND_URL',
    'https://inventorymanagement-api-production.up.railway.app'
)

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes", # tracks django models 
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "cloudinary_storage",
    "cloudinary",

    "rest_framework",
    "drf_spectacular",
    "django_filters",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "social_django", #social authentication such as Google OAuth

    "tenants",

    "products",
    "warehouses",
    "inventory",
    "orders",
    "reports",
    "accounts",
    "reviews",
    "coupons",
    "wishlist",
    "notifications",
    "cart",
    "payment",
]

# MIDDLEWARE list of middleware components (process requests/responses in order)

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
    "tenants.middleware.TenantMiddleware",
]

# URLS

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

# TEMPLATES

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "email_templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# DATABASE

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=0,   # Neon serverless: don't reuse connections across requests
            ssl_require=True, # Neon requires SSL — already in URL but this is a safety net
            
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE":
            "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "DISABLE_SERVER_SIDE_CURSORS": True,
        }
    }

# AUTH USER   ### uses custom user model instead of default django user model  
AUTH_USER_MODEL = "accounts.CustomUser"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS":{"min_length": 8},
    },
    {
        "NAME":"django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME":"django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# LANGUAGE
LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC" # universal Time coordinated 

USE_I18N = True # enable internationalization 

USE_TZ = True  # use timezone-aware datatimes

# STATIC FILES
STATIC_URL = "/static/"  ## url path for static files (CSS, JS, images)

STATIC_ROOT = BASE_DIR / "staticfiles" # folder where django collects all static files for production

STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

# MEDIA handles user-uploaded files( profile pictures, product images )

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST FRAMEWORK
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),

    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),

    "DEFAULT_SCHEMA_CLASS":
        "drf_spectacular.openapi.AutoSchema",

    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",# search by exact filelds
        "rest_framework.filters.SearchFilter", # search text
        "rest_framework.filters.OrderingFilter", # sort results 
    ),

    "DEFAULT_PAGINATION_CLASS":
        "rest_framework.pagination.PageNumberPagination",

    "PAGE_SIZE": 10,
}

# JWT

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": False, # not to give refresh token each time
    "BLACKLIST_AFTER_ROTATION": True, # old token becomes invalid 
    "AUTH_HEADER_TYPES": ("Bearer",), # format: "Bearer <token>"
}

# SWAGGER

SPECTACULAR_SETTINGS = {
    "TITLE": "Inventory Management API",
    "DESCRIPTION": "Professional Inventory & Order Management API",
    "VERSION": "1.0.0",

    "SERVE_INCLUDE_SCHEMA": False,

    "SCHEMA_PATH_PREFIX": "/api/",

    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
    },

    # Inject X-Tenant-Slug as a named security scheme so it appears
    # in Swagger UI's Authorize dialog alongside the JWT Bearer field.
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "tenants.openapi.add_tenant_auth_to_schema",
    ],
}

# Google OAuth Settings
# GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
# GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('GOOGLE_CLIENT_ID')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
# Add authentication backends
AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2', # google login 
    'django.contrib.auth.backends.ModelBackend', # Normal username/password
)

# CACHE for a faster response 
CACHES = {
    "default": {
        "BACKEND":
        "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION":
        "unique-inventory-cache",
    }
}

""""
cache stores frequently accessed data in RAM for quick retrieval.
"""


ESEWA_SETTINGS = {
    "MERCHANT_ID": "",  # Sandbox test merchant
    "SECRET_KEY": "",  # Sandbox secret key
    "INITIATE_URL": "https://rc-epay.esewa.com.np/api/epay/main/v2/form",
    "SUCCESS_URL": "https://yourdomain.com/api/orders/esewa-verify/",
    "FAILURE_URL": "https://yourdomain.com/payment-failed",
}


KHALTI_SECRET_KEY = os.getenv("KHALTI_SECRET_KEY")
KHALTI_PUBLIC_KEY = os.getenv("KHALTI_PUBLIC_KEY")

WEBSITE_URL = "http://127.0.0.1:8000"

PAYMENT_RETURN_URL = "http://127.0.0.1:8000/api/payments/verify/"
VAT_PERCENTAGE = Decimal("13.00")

JAZZMIN_SETTINGS = {
    "site_title": "Inventory Management",
    "site_header": "Inventory Management",
    "site_brand": "Inventory Management",
    "welcome_sign": "Welcome to Inventory Management Admin",
    "copyright": "Satkriti",
    "show_sidebar": True,
    "navigation_expanded": True,
}