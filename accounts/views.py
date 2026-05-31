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
)


@extend_schema(tags=['auth'], request=RegisterSerializer, responses=RegisterSerializer)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


@extend_schema(tags=['auth'], request=LoginSerializer)
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@extend_schema(tags=['auth'], request=AdminLoginSerializer)
class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@extend_schema(tags=['auth'])
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
        })


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

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