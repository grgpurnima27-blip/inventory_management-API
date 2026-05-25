from rest_framework import generics
from rest_framework.permissions import AllowAny

from drf_spectacular.utils import extend_schema

from .serializers import RegisterSerializer


@extend_schema(
    tags=['auth']
)
class RegisterView(generics.CreateAPIView):

    serializer_class = RegisterSerializer

    permission_classes = [AllowAny]