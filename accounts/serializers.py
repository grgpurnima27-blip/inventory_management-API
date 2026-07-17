from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Profile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer used by MeView and other user responses."""

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "role",
            "is_email_verified",
            "date_joined",
            "last_login",
        ]
        read_only_fields = [
            "id",
            "is_email_verified",
            "date_joined",
            "last_login",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        read_only_fields = ["id"]

    def validate_username(self, value):
        value = value.strip()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Email already exists.")
        return email

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data["email"],
                password=validated_data["password"],
                role="customer",
                is_email_verified=False,
            )
            Profile.objects.get_or_create(user=user)

        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs.get("username"),
            password=attrs.get("password"),
        )

        if not user:
            raise serializers.ValidationError("Invalid username or password.")

        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")

        if not user.is_email_verified:
            raise serializers.ValidationError(
                {
                    "email": (
                        "Please verify your email address before logging in. "
                        "Check your inbox for the verification link."
                    )
                }
            )

        refresh = RefreshToken.for_user(user)
        response = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_email_verified": user.is_email_verified,
            },
        }

        try:
            tenant = user.owned_tenant
        except ObjectDoesNotExist:
            tenant = None

        if tenant is not None:
            response["tenant"] = {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "your_role": "owner",
                "note": f"Use header X-Tenant-Slug: {tenant.slug} in all store requests.",
            }
        else:
            from tenants.models import TenantMember

            memberships = (
                TenantMember.objects.filter(user=user, is_active=True)
                .select_related("tenant")
                .order_by("tenant__name")
            )

            membership_data = [
                {
                    "tenant_id": membership.tenant.id,
                    "tenant_name": membership.tenant.name,
                    "tenant_slug": membership.tenant.slug,
                    "role": membership.role,
                    "note": f"Use header X-Tenant-Slug: {membership.tenant.slug}",
                }
                for membership in memberships
                if membership.tenant.is_active
            ]

            if membership_data:
                response["memberships"] = membership_data

        return response


class AdminLoginSerializer(serializers.Serializer):
    """Login for platform administrators."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs.get("username"),
            password=attrs.get("password"),
        )

        if not user:
            raise serializers.ValidationError("Invalid username or password.")

        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")

        if user.role != "admin":
            raise serializers.ValidationError("Admin access only.")

        if not user.is_email_verified:
            raise serializers.ValidationError(
                {
                    "email": (
                        "Please verify your email address before logging in. "
                        "Check your inbox for the verification link."
                    )
                }
            )

        refresh = RefreshToken.for_user(user)
        response = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_email_verified": user.is_email_verified,
            },
        }

        if user.is_staff or user.is_superuser:
            response["account_type"] = "platform_admin"
            response["note"] = "You manage the platform."
            return response

        try:
            tenant = user.owned_tenant
        except ObjectDoesNotExist:
            tenant = None

        if tenant is not None:
            response["account_type"] = "vendor_admin"
            response["tenant"] = {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "your_role": "owner",
                "is_active": tenant.is_active,
                "note": f"Use header X-Tenant-Slug: {tenant.slug} in all store requests.",
            }
        else:
            response["account_type"] = "admin_no_tenant"
            response["note"] = "No store was found for this account."

        return response


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        if data["old_password"] == data["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from old password."}
            )

        return data

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        help_text="Paste your refresh token here to log out."
    )


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "id",
            "username",
            "email",
            "role",
            "avatar",
            "avatar_url",
            "phone",
            "address",
            "city",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "username",
            "email",
            "role",
            "avatar_url",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "avatar": {"write_only": True},
        }

    def get_avatar_url(self, obj):
        return obj.get_avatar_url()

    def validate_avatar(self, value):
        if not value:
            return value

        if hasattr(value, "size") and value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("Avatar size must not exceed 2 MB.")

        if hasattr(value, "content_type"):
            allowed_types = ["image/jpeg", "image/png", "image/webp"]
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Only JPEG, PNG, and WebP images are allowed."
                )

        return value


class VendorRegisterSerializer(serializers.Serializer):
    """Create a vendor user and inactive tenant in one transaction."""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    store_name = serializers.CharField(max_length=255)
    store_slug = serializers.SlugField(max_length=100)
    store_description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_username(self, value):
        value = value.strip()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return email

    def validate_store_slug(self, value):
        from tenants.models import Tenant

        slug = value.strip().lower()
        if Tenant.objects.filter(slug__iexact=slug).exists():
            raise serializers.ValidationError(
                "A store with this slug already exists. Choose a different one."
            )
        return slug

    def validate_store_name(self, value):
        from tenants.models import Tenant

        name = value.strip()
        if Tenant.objects.filter(name__iexact=name).exists():
            raise serializers.ValidationError(
                "A store with this name already exists."
            )
        return name

    def create(self, validated_data):
        from tenants.models import Tenant

        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data["email"],
                password=validated_data["password"],
                role="admin",
                is_email_verified=False,
            )
            Profile.objects.get_or_create(user=user)

            tenant = Tenant.objects.create(
                name=validated_data["store_name"],
                slug=validated_data["store_slug"],
                description=validated_data.get("store_description", ""),
                owner=user,
                is_active=False,
            )

        return user, tenant


class VendorLoginSerializer(serializers.Serializer):
    """Login for an approved store owner."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs["username"],
            password=attrs["password"],
        )

        if not user:
            raise serializers.ValidationError(
                {"username": "Invalid username or password."}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"username": "This account is inactive."}
            )

        if not user.is_email_verified:
            raise serializers.ValidationError(
                {
                    "email": (
                        "Please verify your email address before logging in. "
                        "Check your inbox for the verification link."
                    )
                }
            )

        if user.role != "admin":
            raise serializers.ValidationError(
                {"username": "This account does not have vendor admin access."}
            )

        try:
            tenant = user.owned_tenant
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                {
                    "username": (
                        "No store was found for this account. "
                        "Contact the platform administrator."
                    )
                }
            )

        if not tenant.is_active:
            raise serializers.ValidationError(
                {
                    "username": (
                        "Your store registration is pending approval by the platform admin. "
                        "You can log in after the store is activated."
                    )
                }
            )

        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_email_verified": user.is_email_verified,
            },
            "store": {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "your_role": "owner",
            },
            "next_step": (
                f"Set X-Tenant-Slug: {tenant.slug} before using store endpoints."
            ),
        }


class EmployeeLoginSerializer(serializers.Serializer):
    """Login for an active manager, staff member, or viewer."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    tenant_slug = serializers.SlugField(
        help_text="Slug of the store where you work."
    )

    def validate(self, attrs):
        user = authenticate(
            username=attrs["username"],
            password=attrs["password"],
        )

        if not user:
            raise serializers.ValidationError(
                {"username": "Invalid username or password."}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"username": "This account is inactive."}
            )

        if not user.is_email_verified:
            raise serializers.ValidationError(
                {
                    "email": (
                        "Please verify your email address before logging in. "
                        "Check your inbox for the verification link."
                    )
                }
            )

        from tenants.models import Tenant, TenantMember

        try:
            tenant = Tenant.objects.get(
                slug=attrs["tenant_slug"],
                is_active=True,
            )
        except Tenant.DoesNotExist:
            raise serializers.ValidationError(
                {"tenant_slug": "Store not found or inactive."}
            )

        try:
            owned_tenant = user.owned_tenant
        except ObjectDoesNotExist:
            owned_tenant = None

        if owned_tenant == tenant:
            raise serializers.ValidationError(
                {
                    "username": (
                        "You are the store owner. "
                        "Use the Vendor Login endpoint instead."
                    )
                }
            )

        try:
            membership = TenantMember.objects.get(
                tenant=tenant,
                user=user,
                is_active=True,
            )
        except TenantMember.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "tenant_slug": (
                        "You are not an active member of this store. "
                        "Ask the store owner to add or activate your membership."
                    )
                }
            )

        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_email_verified": user.is_email_verified,
            },
            "store": {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "your_role": membership.role,
            },
            "next_step": (
                f"Set X-Tenant-Slug: {tenant.slug} before using store endpoints."
            ),
        }


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return data