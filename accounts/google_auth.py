import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiResponse

User = get_user_model()


class GoogleAuthView(APIView):
    permission_classes = []
    
    @extend_schema(
        summary='Google Sign In',
        description='Authenticate user with Google OAuth2 token',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'access_token': {'type': 'string', 'description': 'Google OAuth access token'}
                },
                'required': ['access_token']
            }
        },
        responses={
            200: OpenApiResponse(description='Successfully authenticated'),
            400: OpenApiResponse(description='Invalid token'),
            401: OpenApiResponse(description='Authentication failed'),
        },
        tags=['auth']
    )
    def post(self, request):
        access_token = request.data.get('access_token')
        
        if not access_token:
            return Response(
                {'error': 'Access token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify token with Google
        google_url = f'https://www.googleapis.com/oauth2/v3/userinfo?access_token={access_token}'
        
        try:
            response = requests.get(google_url)
            google_data = response.json()
            
            if response.status_code != 200:
                return Response(
                    {'error': 'Invalid Google token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            email = google_data.get('email')
            
            if not email:
                return Response(
                    {'error': 'Email not provided by Google'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': google_data.get('given_name', ''),
                    'last_name': google_data.get('family_name', ''),
                    'is_email_verified': True,
                }
            )
            
            # Generate JWT tokens
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
            
        except requests.RequestException as e:
            return Response(
                {'error': f'Failed to verify Google token: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {'error': f'Authentication failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GoogleLoginURLView(APIView):
    permission_classes = []
    
    @extend_schema(
        summary='Get Google Login URL',
        description='Returns the URL to redirect users for Google OAuth',
        responses={
            200: OpenApiResponse(description='URL returned successfully'),
        },
        tags=['auth']
    )
    def get(self, request):
        redirect_uri = request.build_absolute_uri('/api/auth/google/callback/')
        auth_url = f'https://accounts.google.com/o/oauth2/v2/auth?client_id={settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY}&redirect_uri={redirect_uri}&response_type=code&scope=email profile'
        
        return Response({
            'auth_url': auth_url
        })