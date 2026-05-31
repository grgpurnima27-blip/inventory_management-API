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
        serializer.save()

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

        #### Build timeline — only show stages that have happened
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
                #Show pending future stages
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

        # Valid transitions only
        valid_transitions = {
            Order.STATUS_PENDING: [Order.STATUS_PROCESSING, Order.STATUS_CANCELLED],
            Order.STATUS_PROCESSING: [Order.STATUS_SHIPPED, Order.STATUS_CANCELLED],
            Order.STATUS_SHIPPED: [Order.STATUS_COMPLETED],
            Order.STATUS_COMPLETED: [],
            Order.STATUS_CANCELLED: [],
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

        #Set timestamp for the new stage
        now = timezone.now()
        timestamp_map = {
            Order.STATUS_PROCESSING: 'processed_at',
            Order.STATUS_SHIPPED: 'shipped_at',
            Order.STATUS_COMPLETED: 'completed_at',
            Order.STATUS_CANCELLED: 'cancelled_at',
        }

        order.status = new_status
        timestamp_field = timestamp_map.get(new_status)
        if timestamp_field:
            setattr(order, timestamp_field, now)

        order.save()

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
        summary='Get eSewa Payment QR',
        description='Generates an eSewa payment QR for the exact order amount.',
        responses={
            200: OpenApiResponse(description='QR code generated successfully.'),
            400: OpenApiResponse(description='Order is cancelled.'),
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
        order = self.get_object()

        if request.user.role != 'admin' and order.user != request.user:
            return Response(
                {'error': 'You can only pay for your own orders.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if order.status == Order.STATUS_CANCELLED:
            return Response(
                {'error': 'Cannot generate QR for a cancelled order.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        esewa_url = (
            f"esewa://payment?"
            f"amount={order.total_price}&"
            f"remarks=Order%23{order.id}&"
            f"pid=ORDER-{order.id}"
        )

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(esewa_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color='#60BB46', back_color='white')

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return Response(
            {
                'order_id': order.id,
                'customer_name': order.customer_name,
                'amount': str(order.total_price),
                'currency': 'NPR',
                'payment_method': 'eSewa',
                'esewa_url': esewa_url,
                'qr_code': f'data:image/png;base64,{qr_base64}',
                'instructions': (
                    f'Open eSewa app → Scan QR → '
                    f'Confirm payment of NPR {order.total_price}'
                ),
            },
            status=status.HTTP_200_OK
        )