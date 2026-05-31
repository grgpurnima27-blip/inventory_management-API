from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from .models import Wishlist
from .serializers import WishlistReadSerializer, WishlistWriteSerializer


@extend_schema(tags=['wishlist'])
class WishlistViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Each user only sees their own wishlist
        return Wishlist.objects.filter(
            user=self.request.user
        ).select_related('product')

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return WishlistReadSerializer
        return WishlistWriteSerializer

    @extend_schema(
        summary='My Wishlist',
        description='Get all products in your wishlist.',
        responses=WishlistReadSerializer,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Add to Wishlist',
        description='Add a product to your wishlist.',
        request=WishlistWriteSerializer,
        examples=[
            OpenApiExample(
                name='Add to Wishlist Example',
                value={'product': 1},
                request_only=True,
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary='Remove from Wishlist',
        description='Remove a product from your wishlist.',
        responses={204: OpenApiResponse(description='Removed successfully.')}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary='Clear Wishlist',
        description='Remove all products from your wishlist.',
        responses={200: OpenApiResponse(description='Wishlist cleared.')},
    )
    @action(
        detail=False,
        methods=['delete'],
        url_path='clear'
    )
    def clear(self, request):
        count, _ = Wishlist.objects.filter(user=request.user).delete()
        return Response(
            {'message': f'Wishlist cleared. {count} item(s) removed.'},
            status=status.HTTP_200_OK
        )

    #  Block update — wishlist items are add/remove only
    def update(self, request, *args, **kwargs):
        return Response(
            {'error': 'Use add or remove instead.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {'error': 'Use add or remove instead.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )