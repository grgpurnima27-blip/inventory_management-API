from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

from rest_framework import serializers

from rest_framework_simplejwt.tokens import RefreshToken

from .models import Profile


User = get_user_model()


# ADD THIS USER SERIALIZER
class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model - used for MeView and user responses"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']


class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        read_only_fields = ['id']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                'Username already exists.'
            )
        return value



    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists.')
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role='customer'
            ## is_email_verified=False
        )
        Profile.objects.create(user=user)
        return user


class LoginSerializer(serializers.Serializer):

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs.get('username'),
            password=attrs.get('password')
        )
        if not user:
            raise serializers.ValidationError('Invalid username or password.')

        if not user.is_email_verified:
            raise serializers.ValidationError('Email is not verified.')

        refresh = RefreshToken.for_user(user)
        response = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
            }
        }

        # If the user owns a store, return their tenant so the client
        # knows which X-Tenant-Slug to send for future requests.
        try:
            tenant = user.owned_tenant
            response['tenant'] = {
                'id': tenant.id,
                'name': tenant.name,
                'slug': tenant.slug,
                'your_role': 'owner',
                'note': f'Use header  X-Tenant-Slug: {tenant.slug}  in all store requests.',
            }
        except Exception:
            # Check if this user is a member of any store
            from tenants.models import TenantMember
            memberships = list(
                TenantMember.objects.filter(user=user, is_active=True)
                .select_related('tenant')
            )
            if memberships:
                response['memberships'] = [
                    {
                        'tenant_id':   m.tenant.id,
                        'tenant_name': m.tenant.name,
                        'tenant_slug': m.tenant.slug,
                        'role':        m.role,
                        'note':        f'Use header  X-Tenant-Slug: {m.tenant.slug}',
                    }
                    for m in memberships
                ]

        return response


class AdminLoginSerializer(serializers.Serializer):
    """
    Login for vendor admins (store owners) and platform admins.
    Returns tenant info so the client knows the X-Tenant-Slug to use.
    For employees, use POST /api/tenants/login/ instead.
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs.get('username'),
            password=attrs.get('password')
        )
        if not user:
            raise serializers.ValidationError('Invalid username or password.')
        if user.role != 'admin':
            raise serializers.ValidationError('Admin access only.')
        if not user.is_email_verified:
            raise serializers.ValidationError('Email is not verified.')

        refresh = RefreshToken.for_user(user)
        response = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
            }
        }

        # Platform admin (is_staff) — no tenant, manages the platform itself
        if user.is_staff:
            response['account_type'] = 'platform_admin'
            response['note'] = 'You manage the platform. Use POST /api/tenants/ to create stores.'
            return response

        # Vendor admin — return their owned store
        try:
            tenant = user.owned_tenant
            response['account_type'] = 'vendor_admin'
            response['tenant'] = {
                'id': tenant.id,
                'name': tenant.name,
                'slug': tenant.slug,
                'your_role': 'owner',
                'note': f'Use header  X-Tenant-Slug: {tenant.slug}  in all store requests.',
            }
        except Exception:
            response['account_type'] = 'admin_no_tenant'
            response['note'] = 'No store found. Ask a platform admin to create a tenant for you.'

        return response


class ChangePasswordSerializer(serializers.Serializer):

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError({
                'new_password': 'New password must be different from old password.'
            })
        return data

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class LogoutSerializer(serializers.Serializer):

    refresh = serializers.CharField(
        help_text='Paste your refresh token here to logout.'
    )


class ProfileSerializer(serializers.ModelSerializer):

    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)

    ### Shows generated or uploaded avatar URL
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'id',
            'username',
            'email',
            'role',
            'avatar',           
            'avatar_url',
            'phone',
            'address',
            'city',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'avatar_url']
        extra_kwargs = {
            'avatar': {'write_only': True}  ### hide raw cloudinary field
        }

    def get_avatar_url(self, obj):
        return obj.get_avatar_url()

    def validate_avatar(self, value):
        if value:
            if hasattr(value, 'size') and value.size > 2 * 1024 * 1024:
                raise serializers.ValidationError(
                    'Avatar size must not exceed 2MB.'
                )
            if hasattr(value, 'content_type'):
                allowed = ['image/jpeg', 'image/png', 'image/webp']
                if value.content_type not in allowed:
                    raise serializers.ValidationError(
                        'Only JPEG, PNG, and WebP images are allowed.'
                    )
        return value


class VendorRegisterSerializer(serializers.Serializer):
    """
    One-step vendor registration.
    Creates a CustomUser (role='admin') + Tenant (is_active=False) atomically.
    The store stays inactive until a platform admin approves it.
    """
    username          = serializers.CharField(max_length=150)
    email             = serializers.EmailField()
    password          = serializers.CharField(write_only=True, min_length=8)
    store_name        = serializers.CharField(max_length=255)
    store_slug        = serializers.SlugField(max_length=100)
    store_description = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate_store_slug(self, value):
        from tenants.models import Tenant
        if Tenant.objects.filter(slug=value).exists():
            raise serializers.ValidationError('A store with this slug already exists. Choose a different one.')
        return value

    def validate_store_name(self, value):
        from tenants.models import Tenant
        if Tenant.objects.filter(name=value).exists():
            raise serializers.ValidationError('A store with this name already exists.')
        return value

    def create(self, validated_data):
        from django.db import transaction
        from tenants.models import Tenant

        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                password=validated_data['password'],
                role='admin',
            )
            user.is_email_verified = True
            user.save()
            Profile.objects.create(user=user)

            tenant = Tenant.objects.create(
                name=validated_data['store_name'],
                slug=validated_data['store_slug'],
                description=validated_data.get('store_description', ''),
                owner=user,
                is_active=False,
            )

        return user, tenant


class VendorLoginSerializer(serializers.Serializer):
    """
    Login for store owners (vendor admins).
    The account must have role='admin' and own a tenant store.
    Returns the JWT token and the tenant slug to use as X-Tenant-Slug.
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError({'username': 'Invalid username or password.'})
        if not user.is_email_verified:
            raise serializers.ValidationError({'username': 'Email is not verified.'})
        if user.role != 'admin':
            raise serializers.ValidationError({'username': 'This account does not have vendor admin access.'})

        try:
            tenant = user.owned_tenant
        except Exception:
            raise serializers.ValidationError({
                'username': 'No store found for this account. Contact the platform admin.'
            })

        if not tenant.is_active:
            raise serializers.ValidationError({
                'username': (
                    'Your store registration is pending approval by the platform admin. '
                    'You will be able to log in once your store is activated.'
                )
            })

        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access':  str(refresh.access_token),
            'user': {
                'id':       user.id,
                'username': user.username,
                'email':    user.email,
            },
            'store': {
                'id':         tenant.id,
                'name':       tenant.name,
                'slug':       tenant.slug,
                'your_role':  'owner',
            },
            'next_step': (
                f'Copy the slug and set  X-Tenant-Slug: {tenant.slug}  '
                f'in the Authorize dialog (tenantAuth field) before using store endpoints.'
            ),
        }


class EmployeeLoginSerializer(serializers.Serializer):
    """
    Login for store employees (manager / staff / viewer).
    The user must be added to the store by the owner via POST /api/tenant-members/.
    Returns the JWT token, the employee's role, and the tenant slug.
    """
    username    = serializers.CharField()
    password    = serializers.CharField(write_only=True)
    tenant_slug = serializers.SlugField(
        help_text='Slug of the store you work at (e.g. techmart). Ask your store owner for this.'
    )

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError({'username': 'Invalid username or password.'})
        if not user.is_email_verified:
            raise serializers.ValidationError({'username': 'Email is not verified.'})

        from tenants.models import Tenant, TenantMember

        try:
            tenant = Tenant.objects.get(slug=attrs['tenant_slug'], is_active=True)
        except Tenant.DoesNotExist:
            raise serializers.ValidationError({'tenant_slug': 'Store not found or inactive.'})

        # Owners must use the vendor login endpoint
        try:
            if user.owned_tenant == tenant:
                raise serializers.ValidationError({
                    'username': 'You are the store owner. Use the Vendor Login endpoint instead.'
                })
        except Exception:
            pass

        try:
            membership = TenantMember.objects.get(tenant=tenant, user=user, is_active=True)
        except TenantMember.DoesNotExist:
            raise serializers.ValidationError({
                'tenant_slug': (
                    'You are not a member of this store. '
                    'Ask your store owner to add you via /api/tenant-members/.'
                )
            })

        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access':  str(refresh.access_token),
            'user': {
                'id':       user.id,
                'username': user.username,
                'email':    user.email,
            },
            'store': {
                'id':         tenant.id,
                'name':       tenant.name,
                'slug':       tenant.slug,
                'your_role':  membership.role,
            },
            'next_step': (
                f'Copy the slug and set  X-Tenant-Slug: {tenant.slug}  '
                f'in the Authorize dialog (tenantAuth field) before using store endpoints.'
            ),
        }


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        return data