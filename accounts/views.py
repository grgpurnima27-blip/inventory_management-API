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


@extend_schema(tags=['auth'], request=RegisterSerializer)
class RegisterView(generics.CreateAPIView):
    serializer_class   = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # #Generate token and send verification email
        # token = generate_token(user.id, 'verify_email')
        # send_verification_email(user, token)

        # return Response(
        #     {
        #         'message': (
        #             f'Registration successful! '
        #             f'Please check {user.email} to verify your account before logging in.'
        #         )
        #     },
        #     status=status.HTTP_201_CREATED
        # )
        user.is_email_verified = True
        user.save()
        
        # Generate tokens for immediate login
        refresh = RefreshToken.for_user(user)
        
        return Response(
            {
                'message': 'Registration successful!',
                'user_id': user.id,
                'username': user.username,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['auth'], request=LoginSerializer)
class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class   = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@extend_schema(tags=['auth'], request=AdminLoginSerializer)
class AdminLoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class   = AdminLoginSerializer

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['auth'],
    responses={200: UserSerializer},
    description="Get current authenticated user's information"
)
class MeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = UserSerializer

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = ChangePasswordSerializer

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
    serializer_class   = LogoutSerializer

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
    parser_classes     = [MultiPartParser, FormParser, JSONParser]
    serializer_class   = ProfileSerializer

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


class VerifyEmailView(APIView):
    """
    ✅ Email Verification
    User clicks the link in their email → this view runs → sets is_email_verified=True
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Verify Email',
        description='Verify user email using the token sent after registration.',
        responses={
            200: OpenApiResponse(description='Email verified successfully.'),
            400: OpenApiResponse(description='Invalid or expired token.'),
        },
        tags=['auth']
    )
    def get(self, request, token):
        user_id = verify_token(token, 'verify_email')

        if not user_id:
            return Response(
                {'error': 'Invalid or expired verification link. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_email_verified:
            return Response(
                {'message': 'Email is already verified. You can login.'},
                status=status.HTTP_200_OK
            )

        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])

        return Response(
            {'message': 'Email verified successfully! You can now login.'},
            status=status.HTTP_200_OK
        )


class ResendVerificationView(APIView):
    """
    ✅ Resend Verification Email
    If user didn't receive or link expired, they can request a new one
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Resend Verification Email',
        description='Resend email verification link to the user.',
        responses={
            200: OpenApiResponse(description='Verification email sent.'),
            400: OpenApiResponse(description='Email already verified.'),
        },
        tags=['auth']
    )
    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response(
                {'error': 'Email is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if email exists for security
            return Response(
                {'message': 'If this email exists, a verification link has been sent.'},
                status=status.HTTP_200_OK
            )

        if user.is_email_verified:
            return Response(
                {'error': 'This email is already verified. Please login.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        token = generate_token(user.id, 'verify_email')
        send_verification_email(user, token)

        return Response(
            {'message': 'Verification email sent successfully. Please check your inbox.'},
            status=status.HTTP_200_OK
        )


class ForgotPasswordView(APIView):
    """
    ✅ Forgot Password
    User enters email → receives reset link
    """
    permission_classes = [AllowAny]
    serializer_class   = ForgotPasswordSerializer

    @extend_schema(
        summary='Forgot Password',
        description='Send password reset link to user email.',
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(description='Password reset email sent if account exists.'),
        },
        tags=['auth']
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
            token = generate_token(user.id, 'reset_password')
            send_password_reset_email(user, token)
        except User.DoesNotExist:
            pass  # Don't reveal if email exists

        return Response(
            {'message': 'If an account with this email exists, a password reset link has been sent.'},
            status=status.HTTP_200_OK
        )


class ResetPasswordView(APIView):
    """
    ✅ Reset Password
    User clicks reset link in email → enters new password → password updated
    """
    permission_classes = [AllowAny]
    serializer_class   = ResetPasswordSerializer

    @extend_schema(
        summary='Reset Password',
        description='Reset password using the token sent to user email. Token expires in 1 hour.',
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description='Password reset successfully.'),
            400: OpenApiResponse(description='Invalid or expired token.'),
        },
        tags=['auth']
    )
    def post(self, request, token):
        # ✅ Password reset token expires in 1 hour (3600 seconds)
        user_id = verify_token(token, 'reset_password', max_age_seconds=3600)

        if not user_id:
            return Response(
                {'error': 'Invalid or expired reset link. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.set_password(serializer.validated_data['password'])
        user.save()

        return Response(
            {'message': 'Password reset successfully. You can now login with your new password.'},
            status=status.HTTP_200_OK
        )