from rest_framework import serializers
from .models import Coupon


class CouponSerializer(serializers.ModelSerializer):

    class Meta:
        model = Coupon
        fields = [
            'id',
            'code',
            'discount_type',
            'discount_value',
            'minimum_order_amount',
            'max_uses',
            'used_count',
            'is_active',
            'expires_at',
            'created_at',
        ]
        read_only_fields = ['id', 'used_count', 'created_at']

class ValidateCouponSerializer(serializers.Serializer):

    code = serializers.CharField()

    order_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def validate(self, data):

        code = data["code"].upper()
        order_amount = data["order_amount"]
        tenant = getattr(self.context.get("request"), "tenant", None)

        try:
            queryset = Coupon.objects.filter(code=code)

            if tenant:
                queryset = queryset.filter(tenant=tenant)

            coupon = queryset.get()

        except Coupon.DoesNotExist:
            raise serializers.ValidationError(
                {"code": "Coupon code not found."}
            )

        valid, message = coupon.is_valid()

        if not valid:
            raise serializers.ValidationError(
                {"code": message}
            )

        if order_amount < coupon.minimum_order_amount:
            raise serializers.ValidationError(
                {
                    "code": f"Minimum order amount is NPR {coupon.minimum_order_amount}."
                }
            )

        data["coupon"] = coupon

        return data
    
class ApplyCouponSerializer(serializers.Serializer):

    code = serializers.CharField(
        help_text='Enter coupon code to apply at checkout.'
    )
    order_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Total order amount before discount.'
    )

    def validate(self, data):
        code = data['code'].upper()
        order_amount = data['order_amount']
        tenant = getattr(self.context.get('request'), 'tenant', None)

        try:
            qs = Coupon.objects.filter(code=code)
            if tenant:
                qs = qs.filter(tenant=tenant)
            coupon = qs.get()
        except Coupon.DoesNotExist:
            raise serializers.ValidationError({
                'code': 'Coupon code not found.'
            })

        is_valid, message = coupon.is_valid()
        if not is_valid:
            raise serializers.ValidationError({'code': message})

        if order_amount < coupon.minimum_order_amount:
            raise serializers.ValidationError({
                'code': (
                    f'Minimum order amount for this coupon is '
                    f'NPR {coupon.minimum_order_amount}.'
                )
            })

        # Calculate discounted amount
        if coupon.discount_type == Coupon.TYPE_PERCENTAGE:
            discount = (coupon.discount_value / 100) * order_amount
        else:
            discount = coupon.discount_value

        # Discount can't exceed order amount
        discount = min(discount, order_amount)
        final_amount = order_amount - discount

        data['coupon'] = coupon
        data['discount'] = discount
        data['final_amount'] = final_amount
        return data