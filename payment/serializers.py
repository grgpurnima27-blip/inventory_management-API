from rest_framework import serializers

from .models import Payment, PaymentLog, Payout
from orders.models import Order

class PaymentSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source="order.id", read_only=True)
    customer = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order_id",
            "customer",
            "amount",
            "payment_method",
            "transaction_id",
            "gateway_reference",
            "status",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields

class PaymentDetailSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source="order.id", read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"

class InitiatePaymentSerializer(serializers.Serializer):

    order_id = serializers.IntegerField()

    payment_method = serializers.ChoiceField(
        choices=[
            Payment.METHOD_ESEWA,
            Payment.METHOD_KHALTI,
            Payment.METHOD_COD,
        ]
    )

    def validate_order_id(self, value):

        try:
            order = Order.objects.get(id=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError(
                "Order does not exist."
            )

        if order.payment_status == Order.PAYMENT_STATUS_PAID:
            raise serializers.ValidationError(
                "This order has already been paid."
            )

        return value
    
class VerifyPaymentSerializer(serializers.Serializer):

    transaction_id = serializers.CharField()

    gateway_reference = serializers.CharField()

class RefundPaymentSerializer(serializers.Serializer):

    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
    )

class PaymentLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentLog
        fields = "__all__"

class PayoutSerializer(serializers.ModelSerializer):

    tenant = serializers.StringRelatedField()

    class Meta:
        model = Payout
        fields = "__all__"