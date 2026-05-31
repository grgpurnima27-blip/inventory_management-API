from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

import requests
import cloudinary.uploader
from django.conf import settings

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from config.permissions import IsAdminRole
from .models import Product
from .serializers import ProductReadSerializer, ProductWriteSerializer


@extend_schema(tags=['products'])
class ProductViewSet(viewsets.ModelViewSet):

    queryset = Product.objects.all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = ['name', 'category', 'sku']
    ordering_fields = ['price', 'created_at', 'name']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminRole()]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ProductReadSerializer
        return ProductWriteSerializer

    @extend_schema(
        summary='List all products',
        responses=ProductReadSerializer,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Retrieve a product',
        responses=ProductReadSerializer,
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary='Create a product (Admin only)',
        request=ProductWriteSerializer,
        examples=[
            OpenApiExample(
                name='Create Product Example',
                value={
                    'name': 'Dell Inspiron 15',
                    'sku': 'DELL-INS-15-001',
                    'category': 'Laptops',
                    'price': '85000.00',
                },
                request_only=True,
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary='Update a product (Admin only)',
        request=ProductWriteSerializer,
        examples=[
            OpenApiExample(
                name='Update Product Example',
                value={
                    'name': 'Dell Inspiron 15 Updated',
                    'sku': 'DELL-INS-15-001',
                    'category': 'Laptops',
                    'price': '90000.00',
                },
                request_only=True,
            )
        ]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary='Partial update a product (Admin only)',
        request=ProductWriteSerializer,
        examples=[
            OpenApiExample(
                name='Partial Update Example',
                value={'price': '90000.00'},
                request_only=True,
            )
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(summary='Delete a product (Admin only)')
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary='Upload product image (Admin only)',
        description='Manually upload an image — saved to Cloudinary.',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'image': {'type': 'string', 'format': 'binary'}
                }
            }
        },
        responses={
            200: OpenApiResponse(description='Image uploaded to Cloudinary.'),
            400: OpenApiResponse(description='Validation error.'),
        },
        tags=['products']
    )
    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[IsAdminRole],
        url_path='upload-image'
    )
    def upload_image(self, request, pk=None):
        product = self.get_object()

        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        image = request.FILES['image']

        if image.size > 2 * 1024 * 1024:
            return Response(
                {'error': 'Image size must not exceed 2MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        allowed = ['image/jpeg', 'image/png', 'image/webp']
        if image.content_type not in allowed:
            return Response(
                {'error': 'Only JPEG, PNG, and WebP images are allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            image,
            folder='products/',
            public_id=f'product_{product.id}',
            overwrite=True,
        )

        product.image = result['public_id']
        product.save()

        return Response(
            {
                'message': 'Image uploaded to Cloudinary successfully.',
                'image_url': result['secure_url'],
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary='Auto-fetch product image from Pexels (Admin only)',
        description=(
            'Automatically searches Pexels for a photo matching '
            'the product name and saves it to Cloudinary. '
            'No need to upload manually.'
        ),
        responses={
            200: OpenApiResponse(description='Image fetched and saved to Cloudinary.'),
            404: OpenApiResponse(description='No image found on Pexels.'),
            503: OpenApiResponse(description='Pexels API unavailable.'),
        },
        tags=['products']
    )
    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAdminRole],
        url_path='fetch-image'
    )
    def fetch_image(self, request, pk=None):
        product = self.get_object()

        #### Search Pexels by product name
        headers = {'Authorization': settings.PEXELS_API_KEY}
        params = {'query': product.name, 'per_page': 1}

        try:
            response = requests.get(
                'https://api.pexels.com/v1/search',
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            return Response(
                {'error': f'Pexels API error: {str(e)}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        photos = data.get('photos', [])
        if not photos:
            return Response(
                {
                    'error': (
                        f'No image found on Pexels for "{product.name}". '
                        f'Try uploading manually instead.'
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        ### Get best quality image URL from Pexels
        image_url = photos[0]['src']['large']

        ### Upload directly from Pexels URL to Cloudinary
        result = cloudinary.uploader.upload(
            image_url,
            folder='products/',
            public_id=f'product_{product.id}',
            overwrite=True,
        )

        product.image = result['public_id']
        product.save()

        return Response(
            {
                'message': (
                    f'Image for "{product.name}" fetched from '
                    f'Pexels and saved to Cloudinary.'
                ),
                'image_url': result['secure_url'],
                'photographer': photos[0].get('photographer', 'Unknown'),
                'pexels_photo_url': photos[0].get('url', ''),
            },
            status=status.HTTP_200_OK
        )