import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import Profile

User = get_user_model()


def _generate_unique_username(base):
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{counter}"
        counter += 1
    return username


class GoogleAuthView(APIView):
    permission_classes = []

    @extend_schema(
        summary='Google Sign In',
        description=(
            'Authenticate with a Google OAuth2 access token. Returns JWT tokens. '
            'Creates a new account if the email does not exist — '
            '`city` is required for new accounts.'
        ),
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'access_token': {'type': 'string', 'description': 'Google OAuth access token'},
                    'city': {'type': 'string', 'description': 'User city (required for new accounts)'},
                },
                'required': ['access_token']
            }
        },
        responses={
            200: OpenApiResponse(description='Successfully authenticated'),
            400: OpenApiResponse(description='Missing or invalid token'),
            401: OpenApiResponse(description='Google rejected the token'),
        },
        tags=['auth']
    )
    def post(self, request):
        access_token = request.data.get('access_token')
        city = request.data.get('city', '').strip()

        if not access_token:
            return Response(
                {'error': 'access_token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try: # core of Google sign in 
            response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                params={'access_token': access_token},
                timeout=10,
            )
        except requests.RequestException as e:
            return Response(
                {'error': f'Could not reach Google: {str(e)}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        if response.status_code != 200:
            return Response(
                {'error': 'Invalid or expired Google token'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        google_data = response.json()
        email = google_data.get('email')

        if not email:
            return Response(
                {'error': 'Google did not return an email address'},
                status=status.HTTP_400_BAD_REQUEST
            )

        is_new_email = not User.objects.filter(email=email).exists()
        if is_new_email and not city:
            return Response(
                {'error': 'city is required for new accounts.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': _generate_unique_username(email.split('@')[0]),
                'first_name': google_data.get('given_name', ''),
                'last_name': google_data.get('family_name', ''),
                'is_email_verified': True,
            }
        )
        if created:
            Profile.objects.create(user=user, city=city)

        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_new_user': created,
                'role': getattr(user, 'role', 'customer'),
            }
        }, status=status.HTTP_200_OK)
