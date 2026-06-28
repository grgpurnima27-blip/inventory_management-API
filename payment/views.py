from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment, PaymentLog, Payout
from .serializers import (
    PaymentSerializer,
    PaymentDetailSerializer,
    RefundPaymentSerializer,
    PaymentLogSerializer,
    PayoutSerializer,
)
from .services import PaymentService


class PaymentHistoryView(generics.ListAPIView):
    """
    List payments for the logged-in user.
    """

    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(
            customer=self.request.user
        ).order_by("-created_at")


class PaymentDetailView(generics.RetrieveAPIView):
    """
    Retrieve payment details.
    """

    serializer_class = PaymentDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(
            customer=self.request.user
        )


class RefundPaymentView(APIView):
    """
    Refund a payment (Admin only).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):

        if getattr(request.user, "role", None) != "admin":
            return Response(
                {
                    "error": "Only admins can refund payments."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        payment = get_object_or_404(
            Payment,
            pk=pk,
        )

        serializer = RefundPaymentSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        PaymentService.refund_payment(
            payment,
            serializer.validated_data.get("reason", "")
        )

        return Response(
            {
                "message": "Payment refunded successfully."
            }
        )


class PaymentLogListView(generics.ListAPIView):
    """
    List payment logs (Admin only).
    """

    serializer_class = PaymentLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        if getattr(self.request.user, "role", None) != "admin":
            return PaymentLog.objects.none()

        return PaymentLog.objects.select_related(
            "payment"
        )


class PayoutListView(generics.ListAPIView):
    """
    Vendor/Admin payout list.
    """

    serializer_class = PayoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        user = self.request.user

        if getattr(user, "role", None) == "admin":
            return Payout.objects.select_related(
                "tenant",
                "order",
            )

        tenant = getattr(user, "tenant", None)

        if tenant:
            return Payout.objects.filter(
                tenant=tenant
            )

        return Payout.objects.none()