from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from rest_framework_simplejwt.serializers import (
    TokenRefreshSerializer
)

from drf_spectacular.utils import extend_schema


@extend_schema(
    tags=['auth'],
    request=TokenRefreshSerializer,
)
class CustomTokenRefreshView(TokenRefreshView):
    pass