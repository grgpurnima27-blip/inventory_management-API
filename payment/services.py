from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from orders.models import Order
from .models import Payment, PaymentLog, Payout


class PaymentService:
    """
    Handles all payment-related business logic.
    """

    COMMISSION_RATE = Decimal("0.10")

    @staticmethod
    @transaction.atomic
    def initiate_payment(order, payment_method, user):
        """
        Create or update a payment for an order.
        """

        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                "customer": user,
                "amount": order.total_price,
                "payment_method": payment_method,
            },
        )

        if not created:
            payment.payment_method = payment_method
            payment.save(update_fields=["payment_method"])

        PaymentLog.objects.create(
            payment=payment,
            event=PaymentLog.EVENT_INITIATED,
            response={
                "message": "Payment initiated."
            },
        )

        return payment

    @staticmethod
    @transaction.atomic
    def mark_payment_success(
        payment,
        transaction_id,
        gateway_reference,
        gateway_response=None,
    ):
        """
        Mark payment as successful and update the related order.
        """

        payment.status = Payment.STATUS_SUCCESS
        payment.transaction_id = transaction_id
        payment.gateway_reference = gateway_reference
        payment.gateway_response = gateway_response
        payment.paid_at = timezone.now()

        payment.save()

        order = payment.order

        order.payment_status = Order.PAYMENT_STATUS_PAID
        order.payment_transaction_id = transaction_id
        order.paid_at = timezone.now()
        order.status = Order.STATUS_PROCESSING

        order.save()

        # Create payouts for vendors
        PaymentService.create_vendor_payouts(order)

        # Reduce product inventory
        PaymentService.update_inventory(order)

        PaymentLog.objects.create(
            payment=payment,
            event=PaymentLog.EVENT_SUCCESS,
            response=gateway_response or {},
        )

        return payment

    @staticmethod
    @transaction.atomic
    def mark_payment_failed(payment, reason):
        """
        Mark payment as failed.
        """

        payment.status = Payment.STATUS_FAILED
        payment.save(update_fields=["status"])

        order = payment.order
        order.payment_status = Order.PAYMENT_STATUS_FAILED
        order.save(update_fields=["payment_status"])

        PaymentLog.objects.create(
            payment=payment,
            event=PaymentLog.EVENT_FAILED,
            response={
                "reason": reason
            },
        )

        return payment

    @staticmethod
    @transaction.atomic
    def refund_payment(payment, reason=""):
        """
        Refund a successful payment.
        """

        payment.status = Payment.STATUS_REFUNDED
        payment.save(update_fields=["status"])

        order = payment.order

        order.payment_status = Order.PAYMENT_STATUS_REFUNDED
        order.save(update_fields=["payment_status"])

        PaymentLog.objects.create(
            payment=payment,
            event=PaymentLog.EVENT_REFUND,
            response={
                "reason": reason
            },
        )

        return payment

    @staticmethod
    @transaction.atomic
    def create_vendor_payouts(order):
        """
        Create payout records for every tenant involved in an order.
        """

        tenant_totals = {}

        for item in order.items.select_related("product__tenant"):

            tenant = item.product.tenant

            # Skip products without tenant
            if tenant is None:
                continue

            item_total = item.quantity * item.unit_price

            tenant_totals[tenant] = (
                tenant_totals.get(tenant, Decimal("0.00"))
                + item_total
            )

        payouts = []

        for tenant, gross_amount in tenant_totals.items():

            commission = gross_amount * PaymentService.COMMISSION_RATE

            net_amount = gross_amount - commission

            payout, created = Payout.objects.get_or_create(
                order=order,
                tenant=tenant,
                defaults={
                    "gross_amount": gross_amount,
                    "commission": commission,
                    "net_amount": net_amount,
                },
            )

            payouts.append(payout)

        return payouts

    @staticmethod
    @transaction.atomic
    def update_inventory(order):
        """
        Reduce inventory after successful payment.
        """

        for item in order.items.select_related("product"):

            product = item.product

            product.quantity -= item.quantity

            if product.quantity < 0:
                product.quantity = 0

            product.save(update_fields=["quantity"])

    @staticmethod
    def verify_payment(payment):
        """
        Placeholder.

        Gateway verification will be implemented in gateway.py.
        """

        return True

    @staticmethod
    def payment_history(user):
        """
        Return payment history for a customer.
        """

        return Payment.objects.filter(
            customer=user
        ).order_by("-created_at")

    @staticmethod
    def get_payment(order):
        """
        Return payment for an order.
        """

        return Payment.objects.filter(
            order=order
        ).first()