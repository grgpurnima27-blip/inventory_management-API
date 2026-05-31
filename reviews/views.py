from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from .models import Review
from .serializers import ReviewReadSerializer, ReviewWriteSerializer


@extend_schema(tags=['reviews'])
class ReviewViewSet(viewsets.ModelViewSet):

    queryset = Review.objects.select_related(
        'user', 'product'
    )

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ReviewReadSerializer
        return ReviewWriteSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]         # anyone can read reviews
        return [IsAuthenticated()]      # must be logged in to write

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by product if provided: /api/reviews/?product=1
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    @extend_schema(
        summary='List all reviews',
        description='Filter by product using ?product=<id>',
        responses=ReviewReadSerializer,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Write a review (Authenticated)',
        description='Only customers who purchased the product can review it.',
        request=ReviewWriteSerializer,
        examples=[
            OpenApiExample(
                name='Review Example',
                value={
                    'product': 1,
                    'rating': 5,
                    'comment': 'Great product, very fast delivery!',
                },
                request_only=True,
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary='Update your review',
        request=ReviewWriteSerializer,
        examples=[
            OpenApiExample(
                name='Update Review Example',
                value={
                    'rating': 4,
                    'comment': 'Updated my review after using it more.',
                },
                request_only=True,
            )
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        review = self.get_object()
        # Only owner can update their review
        if review.user != request.user:
            return Response(
                {'error': 'You can only edit your own reviews.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        review = self.get_object()
        # Only owner or admin can delete
        if review.user != request.user and request.user.role != 'admin':
            return Response(
                {'error': 'You can only delete your own reviews.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)