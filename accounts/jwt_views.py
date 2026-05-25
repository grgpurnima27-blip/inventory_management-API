from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from drf_spectacular.utils import extend_schema


@extend_schema(
    tags=['auth']
)
class CustomTokenObtainPairView(TokenObtainPairView):
    pass


@extend_schema(
    tags=['auth']
)
class CustomTokenRefreshView(TokenRefreshView):
    pass