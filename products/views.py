from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

import os
import requests
import cloudinary.uploader

from drf_spectacular.utils import (
    extend_schema, 
    OpenApiParameter, 
    OpenApiExample, 
    OpenApiResponse,
    inline_serializer
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers

from config.permissions import IsVendorAdmin
from tenants.mixins import TenantViewMixin
from .models import Product
from .serializers import ProductReadSerializer, ProductWriteSerializer


@extend_schema(tags=['products'])
class ProductViewSet(TenantViewMixin, viewsets.ModelViewSet):

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
        return [IsVendorAdmin()]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ProductReadSerializer
        return ProductWriteSerializer

    def get_queryset(self):
        """Filter products by tenant"""
        queryset = super().get_queryset()
        if hasattr(self.request, 'tenant') and self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)
        return queryset

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
        description='Create a new product with optional image upload',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'name': {
                        'type': 'string',
                        'description': 'Product name'
                    },
                    'sku': {
                        'type': 'string',
                        'description': 'Product SKU'
                    },
                    'category': {
                        'type': 'string',
                        'description': 'Product category'
                    },
                    'price': {
                        'type': 'number',
                        'format': 'decimal',
                        'description': 'Product price'
                    },
                    'quantity': {
                        'type': 'integer',
                        'description': 'Stock quantity',
                        'default': 0
                    },
                    'image': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Product image file (JPEG, PNG, WebP, max 2MB)'
                    },
                },
                'required': ['name', 'sku', 'category', 'price']
            }
        },
        responses={
            201: ProductReadSerializer,
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Unauthorized'),
        },
        examples=[
            OpenApiExample(
                name='Create Product Example',
                value={
                    'name': 'Dell Inspiron 15',
                    'sku': 'DELL-INS-15-001',
                    'category': 'Laptops',
                    'price': '85000.00',
                    'quantity': 10,
                },
                request_only=True,
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary='Update a product (Admin only)',
        description='Update a product with optional image upload',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'name': {
                        'type': 'string',
                        'description': 'Product name'
                    },
                    'sku': {
                        'type': 'string',
                        'description': 'Product SKU'
                    },
                    'category': {
                        'type': 'string',
                        'description': 'Product category'
                    },
                    'price': {
                        'type': 'number',
                        'format': 'decimal',
                        'description': 'Product price'
                    },
                    'quantity': {
                        'type': 'integer',
                        'description': 'Stock quantity'
                    },
                    'image': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Product image file (JPEG, PNG, WebP, max 2MB)'
                    },
                }
            }
        },
        responses={
            200: ProductReadSerializer,
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Unauthorized'),
        },
        examples=[
            OpenApiExample(
                name='Update Product Example',
                value={
                    'name': 'Dell Inspiron 15 Updated',
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
        description='Partially update a product with optional image upload',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'name': {
                        'type': 'string',
                        'description': 'Product name'
                    },
                    'sku': {
                        'type': 'string',
                        'description': 'Product SKU'
                    },
                    'category': {
                        'type': 'string',
                        'description': 'Product category'
                    },
                    'price': {
                        'type': 'number',
                        'format': 'decimal',
                        'description': 'Product price'
                    },
                    'quantity': {
                        'type': 'integer',
                        'description': 'Stock quantity'
                    },
                    'image': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Product image file (JPEG, PNG, WebP, max 2MB)'
                    },
                }
            }
        },
        responses={
            200: ProductReadSerializer,
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Unauthorized'),
        },
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
        description='Manually upload an image for a product — saved to Cloudinary.',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'image': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Product image file (JPEG, PNG, WebP, max 2MB)'
                    }
                },
                'required': ['image']
            }
        },
        responses={
            200: inline_serializer(
                name='ImageUploadResponse',
                fields={
                    'message': serializers.CharField(),
                    'image_url': serializers.URLField(),
                }
            ),
            400: OpenApiResponse(description='Validation error - no image or invalid format'),
            401: OpenApiResponse(description='Unauthorized - Admin access required'),
            404: OpenApiResponse(description='Product not found'),
        },
        examples=[
            OpenApiExample(
                name='Success Response',
                value={
                    'message': 'Image uploaded to Cloudinary successfully.',
                    'image_url': 'https://res.cloudinary.com/your-cloud/image/upload/v1234567890/products/product_1.jpg'
                },
                response_only=True,
            ),
        ]
    )
    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[IsVendorAdmin],
        url_path='upload-image'
    )
    def upload_image(self, request, pk=None):
        """Upload a product image to Cloudinary"""
        product = self.get_object()

        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        image = request.FILES['image']

        # Validate image size
        if image.size > 2 * 1024 * 1024:
            return Response(
                {'error': 'Image size must not exceed 2MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate image type
        allowed = ['image/jpeg', 'image/png', 'image/webp']
        if image.content_type not in allowed:
            return Response(
                {'error': 'Only JPEG, PNG, and WebP images are allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                image,
                folder='products/',
                public_id=f'product_{product.id}',
                overwrite=True,
            )

            # Update product with Cloudinary public_id
            product.image = result['public_id']
            product.save(update_fields=['image'])

            return Response(
                {
                    'message': 'Image uploaded to Cloudinary successfully.',
                    'image_url': result['secure_url'],
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Cloudinary upload failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary='Auto-fetch product image from Pexels (Admin only)',
        description=(
            'Automatically searches Pexels for a photo matching '
            'the product name and saves it to Cloudinary. '
            'No need to upload manually.'
        ),
        responses={
            200: inline_serializer(
                name='PexelsFetchResponse',
                fields={
                    'message': serializers.CharField(),
                    'image_url': serializers.URLField(),
                    'photographer': serializers.CharField(),
                    'pexels_photo_url': serializers.URLField(),
                }
            ),
            404: OpenApiResponse(description='No image found on Pexels'),
            503: OpenApiResponse(description='Pexels API unavailable'),
        },
        examples=[
            OpenApiExample(
                name='Success Response',
                value={
                    'message': 'Image for "Dell Inspiron 15" fetched from Pexels and saved to Cloudinary.',
                    'image_url': 'https://res.cloudinary.com/your-cloud/image/upload/v1234567890/products/product_1.jpg',
                    'photographer': 'John Doe',
                    'pexels_photo_url': 'https://www.pexels.com/photo/123456/'
                },
                response_only=True,
            )
        ]
    )
    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsVendorAdmin],
        url_path='fetch-image'
    )
    def fetch_image(self, request, pk=None):
        """Auto-fetch product image from Pexels"""
        product = self.get_object()

        pexels_api_key = os.getenv('PEXELS_API_KEY')

        if not pexels_api_key:
            return Response(
                {'error': 'Pexels API key not configured.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        headers = {'Authorization': pexels_api_key}
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

        # Get best quality image URL from Pexels
        image_url = photos[0]['src']['large']

        try:
            # Upload directly from Pexels URL to Cloudinary
            result = cloudinary.uploader.upload(
                image_url,
                folder='products/',
                public_id=f'product_{product.id}',
                overwrite=True,
            )

            product.image = result['public_id']
            product.save(update_fields=['image'])

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
        except Exception as e:
            return Response(
                {'error': f'Cloudinary upload failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary='Get product image URL',
        description='Get the full Cloudinary URL for a product image',
        responses={
            200: inline_serializer(
                name='ProductImageResponse',
                fields={
                    'id': serializers.IntegerField(),
                    'name': serializers.CharField(),
                    'image_url': serializers.URLField(allow_null=True),
                }
            ),
            404: OpenApiResponse(description='Product not found'),
        }
    )
    @action(
        detail=True,
        methods=['get'],
        url_path='image'
    )
    def get_image_url(self, request, pk=None):
        """Get the full Cloudinary URL for a product's image"""
        product = self.get_object()
        return Response({
            'id': product.id,
            'name': product.name,
            'image_url': product.image.url if product.image else None,
        })