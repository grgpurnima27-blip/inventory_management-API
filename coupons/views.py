from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from config.permissions import IsAdminRole
from .models import Coupon
from .serializers import CouponSerializer, ApplyCouponSerializer


@extend_schema(tags=['coupons'])
class CouponViewSet(viewsets.ModelViewSet):

    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer

    def get_permissions(self):
        # Only admin can create/update/delete coupons
        if self.action in ['apply']:
            return [IsAuthenticated()]
        return [IsAdminRole()]

    @extend_schema(
        summary='Create Coupon (Admin only)',
        examples=[
            OpenApiExample(
                name='Percentage Coupon',
                value={
                    'code': 'SAVE20',
                    'discount_type': 'percentage',
                    'discount_value': '20.00',
                    'minimum_order_amount': '1000.00',
                    'max_uses': 100,
                    'is_active': True,
                    'expires_at': '2026-12-31T00:00:00Z',
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Fixed Amount Coupon',
                value={
                    'code': 'FLAT500',
                    'discount_type': 'fixed',
                    'discount_value': '500.00',
                    'minimum_order_amount': '2000.00',
                    'max_uses': 50,
                    'is_active': True,
                    'expires_at': '2026-12-31T00:00:00Z',
                },
                request_only=True,
            ),
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary='Apply Coupon (Authenticated)',
        description='Check if a coupon is valid and calculate discount.',
        request=ApplyCouponSerializer,
        responses={
            200: OpenApiResponse(description='Coupon applied successfully.'),
            400: OpenApiResponse(description='Invalid coupon.'),
        },
        examples=[
            OpenApiExample(
                name='Apply Coupon Example',
                value={
                    'code': 'SAVE20',
                    'order_amount': '5000.00',
                },
                request_only=True,
            )
        ]
    )
    @action(
        detail=False,
        methods=['post'],
        url_path='apply',
        permission_classes=[IsAuthenticated]
    )
    def apply(self, request):
        serializer = ApplyCouponSerializer(data=request.data)
        if serializer.is_valid():
            coupon = serializer.validated_data['coupon']
            return Response(
                {
                    'code': coupon.code,
                    'discount_type': coupon.discount_type,
                    'discount_value': str(coupon.discount_value),
                    'discount_amount': str(serializer.validated_data['discount']),
                    'original_amount': str(serializer.validated_data['order_amount']),
                    'final_amount': str(serializer.validated_data['final_amount']),
                    'message': f'Coupon applied! You save NPR {serializer.validated_data["discount"]}.',
                },
                status=status.HTTP_200_OK
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )