from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Profile
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    AdminLoginSerializer,
    VendorRegisterSerializer,
    VendorLoginSerializer,
    EmployeeLoginSerializer,
    ChangePasswordSerializer,
    LogoutSerializer,
    ProfileSerializer,
    UserSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)

from .tokens import generate_token, verify_token
from .emails import send_verification_email, send_password_reset_email

User = get_user_model()


@extend_schema(
    tags=['auth'],
    summary='Vendor / Store Owner Registration',
    description=(
        'Register as a new vendor. Creates your personal account and store in one step. '
        'Your store will be **inactive** until a platform admin approves it. '
        'Once approved, use POST /api/auth/vendor/login/ to get your access token.'
    ),
    request=VendorRegisterSerializer,
    responses={
        201: OpenApiResponse(description='Registration submitted. Pending admin approval.'),
        400: OpenApiResponse(description='Validation error — duplicate username, email, or slug.'),
    },
)
class VendorRegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class = VendorRegisterSerializer

    def post(self, request):
        serializer = VendorRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, tenant = serializer.save()
        return Response(
            {
                'message': 'Registration submitted successfully. Your store is pending approval.',
                'user': {
                    'id':       user.id,
                    'username': user.username,
                    'email':    user.email,
                },
                'store': {
                    'name':   tenant.name,
                    'slug':   tenant.slug,
                    'status': 'pending_approval',
                },
                'next_step': (
                    'A platform admin will review and activate your store. '
                    'Then use POST /api/auth/vendor/login/ to get started.'
                ),
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=['auth'], request=RegisterSerializer)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = generate_token(
        user.id,
        "email_verification",
        )

        send_verification_email(
            user,
            token,
        )

        return Response(
            {
                "message": (
                    "Registration successful. "
                    "Please check your email to verify your account."
                ),
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )
        # Auto-verify email (no email sending)
        # user.is_email_verified = True
        # user.save()
        
        # # Generate tokens for immediate login
        # refresh = RefreshToken.for_user(user)
        
        # return Response(
        #     {
        #         'message': 'Registration successful!',
        #         'user_id': user.id,
        #         'username': user.username,
        #         'tokens': {
        #             'refresh': str(refresh),
        #             'access': str(refresh.access_token),
        #         }
        #     },
        #     status=status.HTTP_201_CREATED
        # )


@extend_schema(tags=['auth'], request=LoginSerializer)
class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@extend_schema(tags=['auth'], request=AdminLoginSerializer)
class AdminLoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = AdminLoginSerializer

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['auth'],
    summary='Vendor / Store Owner Login',
    description=(
        'Login for store owners (vendor admins). '
        'The response includes your store slug — paste it into the '
        '**tenantAuth** field in Swagger Authorize to unlock all store endpoints.'
    ),
    request=VendorLoginSerializer,
    responses={
        200: OpenApiResponse(description='Login successful. Returns token + store info.'),
        400: OpenApiResponse(description='Invalid credentials or not a store owner.'),
    },
)
class VendorLoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = VendorLoginSerializer

    def post(self, request):
        serializer = VendorLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['auth'],
    summary='Employee Login',
    description=(
        'Login for store employees (manager / staff / viewer). '
        'You must be added to the store by the owner first via POST /api/tenant-members/. '
        'The response includes your role and the store slug — paste the slug into '
        'the **tenantAuth** field in Swagger Authorize.'
    ),
    request=EmployeeLoginSerializer,
    responses={
        200: OpenApiResponse(description='Login successful. Returns token + store info + your role.'),
        400: OpenApiResponse(description='Invalid credentials or not a member of this store.'),
    },
)
class EmployeeLoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = EmployeeLoginSerializer

    def post(self, request):
        serializer = EmployeeLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['auth'],
    responses={200: UserSerializer},
    description="Get current authenticated user's information"
)
class MeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    @extend_schema(
        summary='Change Password',
        description='Change password for the currently logged-in user.',
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description='Password changed successfully.'),
            400: OpenApiResponse(description='Validation error.'),
        },
        tags=['auth']
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'Password changed successfully. Please log in again.'},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    @extend_schema(
        summary='Logout',
        description='Blacklist the refresh token to log out the current user.',
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(description='Logged out successfully.'),
            400: OpenApiResponse(description='Invalid or expired token.'),
        },
        tags=['auth']
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            try:
                token = RefreshToken(serializer.validated_data['refresh'])
                token.blacklist()
                return Response(
                    {'message': 'Logged out successfully.'},
                    status=status.HTTP_200_OK
                )
            except TokenError:
                return Response(
                    {'error': 'Invalid or expired token.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = ProfileSerializer

    @extend_schema(
        summary='Get Profile',
        description='Get the profile of the currently logged-in user.',
        responses={200: ProfileSerializer},
        tags=['auth']
    )
    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary='Update Profile',
        description='Update profile details and avatar picture.',
        request=ProfileSerializer,
        responses={200: ProfileSerializer},
        tags=['auth']
    )
    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
    """
    Forgot Password - Simplified (no email)
    """
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    @extend_schema(
        summary='Forgot Password',
        description='Password reset functionality - contact admin for password reset.',
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(description='Reset link would be sent if email configured.'),
        },
        tags=['auth']
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        # For now, just return a message since email is disabled
        return Response(
            {
                'message': 'Password reset functionality is currently disabled. Please contact admin at grgpurnima27@gmail.com for password reset assistance.',
                'email': email
            },
            status=status.HTTP_200_OK
        )


class ResetPasswordView(APIView):
    """
    Reset Password - Simplified (no email verification)
    """
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer

    @extend_schema(
        summary='Reset Password',
        description='Reset password (admin only or via email token in production).',
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description='Password reset successfully.'),
            400: OpenApiResponse(description='Invalid request.'),
        },
        tags=['auth']
    )
    def post(self, request, token=None):
        # Simplified - in production this would verify the token
        # For now, this is a placeholder
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # In a real implementation, you'd find the user by token
        return Response(
            {
                'message': 'Password reset functionality is currently disabled. Please contact admin for assistance.',
            },
            status=status.HTTP_200_OK
        )
    
@extend_schema(
    tags=['auth'],
    summary='Verify Email',
    description='Verify a newly registered user email using the token sent by email.',
    responses={
        200: OpenApiResponse(description='Email verified successfully.'),
        400: OpenApiResponse(description='Invalid or expired verification token.'),
        404: OpenApiResponse(description='User not found.'),
    },
)
class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        user_id = verify_token(
            token,
            'email_verification',
        )

        if not user_id:
            return Response(
                {
                    'message': (
                        'Verification link is invalid or has expired.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {
                    'message': 'User not found.'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_email_verified:
            return Response(
                {
                    'message': 'Email is already verified.'
                },
                status=status.HTTP_200_OK,
            )

        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])

        return Response(
            {
                'message': (
                    'Email verified successfully. You can now log in.'
                )
            },
            status=status.HTTP_200_OK,
        )