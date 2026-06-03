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


@extend_schema(tags=['auth'], request=RegisterSerializer, responses=RegisterSerializer)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        token = generate_token(user.id, 'verify_email')
        send_verification_email(user, token)


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
    responses={200: UserSerializer},
    description="Get current authenticated user's information"
)
class MeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
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


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Verify Email',
        description='Verify user registration email using activation token.',
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
                {'error': 'Invalid or expired token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user = User.objects.get(pk=user_id)
            if user.is_email_verified:
                return Response(
                    {'message': 'Email is already verified.'},
                    status=status.HTTP_200_OK
                )
            user.is_email_verified = True
            user.save()
            return Response(
                {'message': 'Email verified successfully.'},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

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
            pass
        return Response(
            {'message': 'If an account with this email exists, a password reset link has been sent.'},
            status=status.HTTP_200_OK
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer

    @extend_schema(
        summary='Reset Password',
        description='Reset password using verification token.',
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description='Password reset successfully.'),
            400: OpenApiResponse(description='Invalid or expired token.'),
        },
        tags=['auth']
    )
    def post(self, request, token):
        user_id = verify_token(token, 'reset_password')
        if not user_id:
            return Response(
                {'error': 'Invalid or expired token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user = User.objects.get(pk=user_id)
            serializer = ResetPasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user.set_password(serializer.validated_data['password'])
            user.save()
            return Response(
                {'message': 'Password reset successfully.'},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_400_BAD_REQUEST
            )