import qrcode
import base64
from io import BytesIO
from django.db import transaction
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from config.permissions import IsAuthenticatedCustomer, IsAdminRole
from inventory.models import Inventory
from .models import Order
from .serializers import OrderSerializer
from notifications.utils import send_notification


class OrderViewSet(viewsets.ModelViewSet):

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticatedCustomer]

    queryset = Order.objects.select_related(
        'user'
    ).prefetch_related(
        'items', 'items__product', 'items__warehouse',
    )

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return self.queryset
        return self.queryset.filter(user=user)

    def perform_create(self, serializer):
        order = serializer.save()
        # Notify user when order is placed
        send_notification(order.user, 'order_placed', order.id)

    def create(self, request, *args, **kwargs):
        """Create order with payment method preference"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get payment method from request (default to COD)
        payment_method = request.data.get('payment_method', Order.PAYMENT_METHOD_COD)
        
        # Save order with payment method
        order = serializer.save(payment_method=payment_method)
        
        # Notify user
        send_notification(order.user, 'order_placed', order.id)
        
        # Prepare response
        response_data = serializer.data
        response_data['payment_method'] = payment_method
        
        # Generate QR code only if user chose eSewa
        if payment_method == Order.PAYMENT_METHOD_ESEWA:
            qr_data = self.generate_payment_qr(order)
            response_data['qr_code'] = qr_data
            response_data['payment_instructions'] = 'Scan this QR code with eSewa app to complete payment'
            response_data['payment_status'] = 'pending'
        else:
            response_data['payment_instructions'] = 'Pay cash upon delivery'
            response_data['payment_status'] = 'pending'
        
        headers = self.get_success_headers(serializer.data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

    def generate_payment_qr(self, order):
        """Generate QR code for eSewa payment"""
        if order.status == Order.STATUS_CANCELLED:
            return None
            
        # eSewa payment 
        esewa_url = (
            f"https://esewa.com.np/epay/main?"
            f"pid=ORDER-{order.id}&"
            f"amt={order.total_price}&"
            f"scd=EPAYTEST"  # Change to your merchant code in production
        )
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(esewa_url)
        qr.make(fit=True)
        
        # Create image with eSewa green color
        img = qr.make_image(fill_color='#60BB46', back_color='white')
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return {
            'qr_code': f'data:image/png;base64,{qr_base64}',
            'amount': str(order.total_price),
            'payment_method': 'eSewa',
            'order_id': order.id,
            'esewa_url': esewa_url,
        }

    def update(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only admins can update orders.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only admins can delete orders.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary='Cancel Order',
        responses={
            200: OpenApiResponse(description='Order cancelled successfully.'),
            400: OpenApiResponse(description='Order already cancelled.'),
            403: OpenApiResponse(description='Not your order.'),
        },
        tags=['orders']
    )
    @transaction.atomic
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()

        if request.user.role != 'admin' and order.user != request.user:
            return Response(
                {'error': 'You can only cancel your own orders.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if order.status == Order.STATUS_CANCELLED:
            return Response(
                {'error': 'Order is already cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if order.status == Order.STATUS_SHIPPED:
            return Response(
                {'error': 'Cannot cancel an order that has already been shipped.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Restore inventory
        for item in order.items.all():
            inventory = Inventory.objects.select_for_update().get(
                product=item.product,
                warehouse=item.warehouse
            )
            inventory.quantity += item.quantity
            inventory.save()

        order.status = Order.STATUS_CANCELLED
        order.cancelled_at = timezone.now()
        order.save()

        # Notify user when order is cancelled
        send_notification(order.user, 'order_cancelled', order.id)

        return Response(
            {'message': 'Order cancelled successfully. Inventory restored.'},
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary='Track Order',
        description='Get full tracking timeline for an order.',
        responses={200: OpenApiResponse(description='Tracking info returned.')},
        tags=['orders']
    )
    @action(
        detail=True,
        methods=['get'],
        url_path='track',
        permission_classes=[IsAuthenticatedCustomer]
    )
    def track(self, request, pk=None):
        order = self.get_object()

        if request.user.role != 'admin' and order.user != request.user:
            return Response(
                {'error': 'You can only track your own orders.'},
                status=status.HTTP_403_FORBIDDEN
            )

        timeline = [
            {
                'stage': 'Order Placed',
                'status': 'completed',
                'timestamp': order.created_at,
            }
        ]

        stages = [
            ('processing', 'Processing', order.processed_at),
            ('shipped', 'Shipped', order.shipped_at),
            ('completed', 'Delivered', order.completed_at),
            ('cancelled', 'Cancelled', order.cancelled_at),
        ]

        for stage_key, stage_label, timestamp in stages:
            if timestamp:
                timeline.append({
                    'stage': stage_label,
                    'status': 'completed',
                    'timestamp': timestamp,
                })
            elif order.status not in [
                Order.STATUS_CANCELLED,
                Order.STATUS_COMPLETED
            ]:
                if stage_key not in ['cancelled']:
                    timeline.append({
                        'stage': stage_label,
                        'status': 'pending',
                        'timestamp': None,
                    })

        return Response(
            {
                'order_id': order.id,
                'customer_name': order.customer_name,
                'current_status': order.status,
                'delivery_city': order.delivery_city,
                'total_price': str(order.total_price),
                'payment_method': order.payment_method,
                'payment_status': order.payment_status,
                'timeline': timeline,
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary='Update Order Status (Admin only)',
        description='Move order through: pending → processing → shipped → completed',
        request=None,
        responses={
            200: OpenApiResponse(description='Status updated.'),
            400: OpenApiResponse(description='Invalid status transition.'),
        },
        tags=['orders'],
        examples=[
            OpenApiExample(
                name='Update Status Example',
                value={'status': 'processing'},
                request_only=True,
            )
        ]
    )
    @action(
        detail=True,
        methods=['patch'],
        url_path='update-status',
        permission_classes=[IsAdminRole]
    )
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')

        valid_transitions = {
            Order.STATUS_PENDING:    [Order.STATUS_PROCESSING, Order.STATUS_CANCELLED],
            Order.STATUS_PROCESSING: [Order.STATUS_SHIPPED, Order.STATUS_CANCELLED],
            Order.STATUS_SHIPPED:    [Order.STATUS_COMPLETED],
            Order.STATUS_COMPLETED:  [],
            Order.STATUS_CANCELLED:  [],
        }

        allowed = valid_transitions.get(order.status, [])

        if new_status not in allowed:
            return Response(
                {
                    'error': (
                        f'Cannot move from "{order.status}" to "{new_status}". '
                        f'Allowed transitions: {allowed}'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        now = timezone.now()
        timestamp_map = {
            Order.STATUS_PROCESSING: 'processed_at',
            Order.STATUS_SHIPPED:    'shipped_at',
            Order.STATUS_COMPLETED:  'completed_at',
            Order.STATUS_CANCELLED:  'cancelled_at',
        }

        order.status = new_status
        timestamp_field = timestamp_map.get(new_status)
        if timestamp_field:
            setattr(order, timestamp_field, now)

        order.save()

        # Notify user when order status changes
        STATUS_NOTIFICATION_MAP = {
            Order.STATUS_PROCESSING: 'order_processing',
            Order.STATUS_SHIPPED:    'order_shipped',
            Order.STATUS_COMPLETED:  'order_completed',
            Order.STATUS_CANCELLED:  'order_cancelled',
        }
        notification_type = STATUS_NOTIFICATION_MAP.get(new_status)
        if notification_type:
            send_notification(order.user, notification_type, order.id)

        return Response(
            {
                'message': f'Order status updated to "{new_status}".',
                'order_id': order.id,
                'status': order.status,
                'updated_at': order.updated_at,
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary='Confirm eSewa Payment',
        description='Confirm payment after eSewa callback',
        responses={
            200: OpenApiResponse(description='Payment confirmed successfully.'),
            400: OpenApiResponse(description='Invalid payment data.'),
        },
        tags=['orders']
    )
    @action(
        detail=True,
        methods=['post'],
        url_path='confirm-payment',
        permission_classes=[IsAuthenticatedCustomer]
    )
    def confirm_payment(self, request, pk=None):
        """Confirm eSewa payment for an order"""
        order = self.get_object()
        
        if request.user.role != 'admin' and order.user != request.user:
            return Response(
                {'error': 'You can only confirm payment for your own orders.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.payment_method != Order.PAYMENT_METHOD_ESEWA:
            return Response(
                {'error': 'This order is not for eSewa payment.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if order.payment_status == 'paid':
            return Response(
                {'error': 'Payment already confirmed for this order.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transaction_id = request.data.get('transaction_id')
        if not transaction_id:
            return Response(
                {'error': 'Transaction ID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update payment status
        order.payment_status = 'paid'
        order.payment_transaction_id = transaction_id
        order.paid_at = timezone.now()
        order.save()
        
        # Optionally auto-update order status to processing
        if order.status == Order.STATUS_PENDING:
            order.status = Order.STATUS_PROCESSING
            order.processed_at = timezone.now()
            order.save()
        
        # Notify user of successful payment
        send_notification(order.user, 'payment_confirmed', order.id)
        
        return Response(
            {
                'message': 'Payment confirmed successfully!',
                'order_id': order.id,
                'payment_status': order.payment_status,
                'transaction_id': order.payment_transaction_id,
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary='Get Payment QR Code',
        description='Get QR code for eSewa payment (only if payment method is eSewa)',
        responses={
            200: OpenApiResponse(description='QR code generated successfully.'),
            400: OpenApiResponse(description='Order not eligible for QR payment.'),
            403: OpenApiResponse(description='Not your order.'),
        },
        tags=['orders']
    )
    @action(
        detail=True,
        methods=['get'],
        url_path='payment-qr',
        permission_classes=[IsAuthenticatedCustomer]
    )
    def payment_qr(self, request, pk=None):
        """Get QR code for eSewa payment"""
        order = self.get_object()

        if request.user.role != 'admin' and order.user != request.user:
            return Response(
                {'error': 'You can only access your own orders.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if order.payment_method != Order.PAYMENT_METHOD_ESEWA:
            return Response(
                {'error': 'This order is not for eSewa payment. Payment method: ' + order.payment_method},
                status=status.HTTP_400_BAD_REQUEST
            )

        if order.payment_status == 'paid':
            return Response(
                {'error': 'This order has already been paid.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if order.status == Order.STATUS_CANCELLED:
            return Response(
                {'error': 'Cannot generate QR for a cancelled order.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        qr_data = self.generate_payment_qr(order)

        return Response(
            {
                'order_id': order.id,
                'customer_name': order.customer_name,
                'amount': str(order.total_price),
                'currency': 'NPR',
                'payment_method': 'eSewa',
                'payment_status': order.payment_status,
                'qr_code': qr_data['qr_code'],
                'esewa_url': qr_data['esewa_url'],
                'instructions': (
                    f'1. Open eSewa app\n'
                    f'2. Scan the QR code\n'
                    f'3. Confirm payment of NPR {order.total_price}\n'
                    f'4. After payment, call confirm-payment endpoint with transaction ID'
                ),
            },
            status=status.HTTP_200_OK
        )