from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.utils import timezone

from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
)

from config.permissions import IsVendorAdmin
from tenants.mixins import TenantViewMixin

from .models import Coupon
from .serializers import (
    CouponSerializer,
    ApplyCouponSerializer,
    ValidateCouponSerializer,
)


@extend_schema(tags=["Coupons"])
class CouponViewSet(TenantViewMixin, viewsets.ModelViewSet):

    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer

    def get_permissions(self):

        if self.action in ["apply", "validate"]:
            return [IsAuthenticated()]

        return [IsVendorAdmin()]

    @extend_schema(
        summary="Create Coupon",
        examples=[
            OpenApiExample(
                "Percentage Coupon",
                value={
                    "code": "SAVE20",
                    "discount_type": "percentage",
                    "discount_value": "20.00",
                    "minimum_order_amount": "1000.00",
                    "max_uses": 100,
                    "is_active": True,
                    "expires_at": "2026-12-31T00:00:00Z",
                },
                request_only=True,
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Validate Coupon",
        description="Checks whether a coupon is valid without applying it.",
        request=ValidateCouponSerializer,
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def validate(self, request):

        serializer = ValidateCouponSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        coupon = serializer.validated_data["coupon"]

        return Response(
            {
                "valid": True,
                "coupon": coupon.code,
                "discount_type": coupon.discount_type,
                "discount_value": coupon.discount_value,
                "minimum_order_amount": coupon.minimum_order_amount,
                "expires_at": coupon.expires_at,
                "message": "Coupon is valid.",
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Expired Coupons",
        description="Returns all expired coupons.",
    )
    @action(
        detail=False,
        methods=["get"],
    )
    def expired(self, request):

        coupons = self.get_queryset().filter(
            expires_at__lt=timezone.now()
        )

        serializer = self.get_serializer(
            coupons,
            many=True,
        )

        return Response(serializer.data)

    @extend_schema(
        summary="Apply Coupon",
        description="Apply a coupon and calculate discount.",
        request=ApplyCouponSerializer,
        responses={
            200: OpenApiResponse(description="Coupon applied successfully."),
            400: OpenApiResponse(description="Invalid coupon."),
        },
        examples=[
            OpenApiExample(
                "Apply Coupon",
                value={
                    "code": "SAVE20",
                    "order_amount": "5000.00",
                },
                request_only=True,
            )
        ],
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def apply(self, request):

        serializer = ApplyCouponSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        coupon = serializer.validated_data["coupon"]

        return Response(
            {
                "code": coupon.code,
                "discount_type": coupon.discount_type,
                "discount_value": str(coupon.discount_value),
                "discount_amount": str(serializer.validated_data["discount"]),
                "original_amount": str(serializer.validated_data["order_amount"]),
                "final_amount": str(serializer.validated_data["final_amount"]),
                "message": f"Coupon applied! You saved NPR {serializer.validated_data['discount']}.",
            },
            status=status.HTTP_200_OK,
        )
    
    