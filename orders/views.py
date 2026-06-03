import qrcode
import base64
from io import BytesIO
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from rest_framework import status, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from config.permissions import IsAuthenticatedCustomer, IsAdminRole
from inventory.models import Inventory
from products.models import Product
from warehouses.models import Warehouse
from .models import Order, OrderItem
from .serializers import OrderSerializer
from notifications.utils import send_notification


class OrderItemCreateSerializer(serializers.Serializer):
    product  = serializers.IntegerField(help_text='Product ID')
    quantity = serializers.IntegerField(help_text='Quantity', min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    customer_name  = serializers.CharField(help_text='Customer full name')
    delivery_city  = serializers.CharField(help_text='Delivery city')
    payment_method = serializers.ChoiceField(
        choices=['esewa', 'cod'],
        default='cod',
        help_text='Payment method'
    )
    items = OrderItemCreateSerializer(many=True, help_text='List of products to order')


class OrderViewSet(viewsets.ModelViewSet):

    serializer_class   = OrderSerializer
    permission_classes = [IsAuthenticatedCustomer]

    queryset = Order.objects.select_related('user').prefetch_related(
        'items', 'items__product', 'items__warehouse',
    )

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return self.queryset
        return self.queryset.filter(user=user)

    @extend_schema(
        summary='Create Order',
        description='Create a new order with items and payment method preference. For eSewa payment, a QR code will be generated.',
        request=OrderCreateSerializer,
        responses={
            201: OrderSerializer,
            400: OpenApiResponse(description='Bad request - invalid data'),
            401: OpenApiResponse(description='Unauthorized - valid token required'),
        },
        tags=['orders'],
        examples=[
            OpenApiExample(
                'eSewa Payment Example',
                description='Order with eSewa payment (QR code will be generated)',
                value={
                    'customer_name': 'priscagurung',
                    'delivery_city': 'Kathmandu',
                    'payment_method': 'esewa',
                    'items': [{'product': 2, 'quantity': 1}]
                },
                request_only=True,
            ),
            OpenApiExample(
                'Cash on Delivery Example',
                description='Order with Cash on Delivery payment',
                value={
                    'customer_name': 'john_doe',
                    'delivery_city': 'Pokhara',
                    'payment_method': 'cod',
                    'items': [
                        {'product': 1, 'quantity': 2},
                        {'product': 3, 'quantity': 1}
                    ]
                },
                request_only=True,
            ),
        ]
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data

        # Validate required fields
        if not data.get('customer_name'):
            return Response(
                {'error': 'customer_name is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        items_data = data.get('items') or data.get('create_items', [])
        if not items_data:
            return Response(
                {'error': 'At least one item is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_method = data.get('payment_method', Order.PAYMENT_METHOD_COD)
        if payment_method not in [Order.PAYMENT_METHOD_ESEWA, Order.PAYMENT_METHOD_COD]:
            return Response(
                {'error': f'Invalid payment_method. Must be "esewa" or "cod".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        delivery_city = data.get('delivery_city', 'Kathmandu')

        # ------------------------------------------------------------------
        # Validate and process items using Decimal to avoid precision issues
        # ------------------------------------------------------------------
        order_items     = []
        original_amount = Decimal('0.00')

        for item in items_data:
            product_id   = item.get('product')
            quantity_val = item.get('quantity', 1)

            try:
                quantity = int(quantity_val)
            except (ValueError, TypeError):
                return Response(
                    {'error': f'Quantity must be a valid integer for product ID {product_id}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not product_id:
                return Response({'error': 'Each item must have a product ID.'}, status=status.HTTP_400_BAD_REQUEST)

            if quantity <= 0:
                return Response({'error': f'Quantity must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                product = Product.objects.get(id=int(product_id))
            except Product.DoesNotExist:
                return Response({'error': f'Product with id {product_id} does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

            # ✅ Find inventory in delivery city warehouse
            inventory = Inventory.objects.select_for_update().filter(
                product=product,
                warehouse__city__iexact=delivery_city,
                quantity__gte=quantity
            ).first()

            if not inventory:
                return Response(
                    {'error': f'Sorry, {product.name} is out of stock in {delivery_city} with the requested quantity.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ✅ Use Decimal for price calculation
            unit_price   = Decimal(str(product.price))
            item_total   = unit_price * quantity
            original_amount += item_total

            order_items.append({
                'product':   product,
                'warehouse': inventory.warehouse,
                'inventory': inventory,
                'quantity':  quantity,
                'unit_price': unit_price,
            })

        # ------------------------------------------------------------------
        # Calculate totals with Decimal
        # ------------------------------------------------------------------
        original_amount = original_amount.quantize(Decimal('0.01'))
        discount_amount = Decimal('0.00')
        total_price     = (original_amount - discount_amount).quantize(Decimal('0.01'))

        # ------------------------------------------------------------------
        # Create order
        # ------------------------------------------------------------------
        try:
            order = Order.objects.create(
                user            = request.user,
                customer_name   = data.get('customer_name'),
                delivery_city   = delivery_city,
                payment_method  = payment_method,
                original_amount = original_amount,
                discount_amount = discount_amount,
                total_price     = total_price,
                status          = Order.STATUS_PENDING,
            )
        except ValidationError as e:
            error_msg = e.message_dict if hasattr(e, 'message_dict') else str(e)
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)

        # ------------------------------------------------------------------
        # Create order items and deduct inventory
        # ------------------------------------------------------------------
        for item_data in order_items:
            OrderItem.objects.create(
                order      = order,
                product    = item_data['product'],
                warehouse  = item_data['warehouse'],
                quantity   = item_data['quantity'],
                unit_price = item_data['unit_price'],
            )
            inv = item_data['inventory']
            inv.quantity -= item_data['quantity']
            inv.save()

        # Notify user
        send_notification(order.user, 'order_placed', order.id)

        # Prepare response
        serializer    = self.get_serializer(order)
        response_data = serializer.data

        # ✅ Generate QR only if eSewa
        if payment_method == Order.PAYMENT_METHOD_ESEWA:
            qr_data = self._generate_payment_qr(order)
            response_data['qr_code']             = qr_data
            response_data['payment_instructions'] = 'Scan this QR code with eSewa app to complete payment'
        else:
            response_data['payment_instructions'] = 'Pay cash upon delivery'

        headers = self.get_success_headers(serializer.data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

    def _generate_payment_qr(self, order):
        """Generate QR code for eSewa payment"""
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

        img    = qr.make_image(fill_color='#60BB46', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return {
            'qr_code':   f'data:image/png;base64,{qr_base64}',
            'amount':    str(order.total_price),
            'esewa_url': esewa_url,
            'order_id':  order.id,
        }

    def update(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': 'Only admins can update orders.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': 'Only admins can delete orders.'}, status=status.HTTP_403_FORBIDDEN)
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
            return Response({'error': 'You can only cancel your own orders.'}, status=status.HTTP_403_FORBIDDEN)

        if order.status == Order.STATUS_CANCELLED:
            return Response({'error': 'Order is already cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

        if order.status == Order.STATUS_SHIPPED:
            return Response({'error': 'Cannot cancel an order that has already been shipped.'}, status=status.HTTP_400_BAD_REQUEST)

        for item in order.items.all():
            inventory = Inventory.objects.select_for_update().get(
                product=item.product,
                warehouse=item.warehouse
            )
            inventory.quantity += item.quantity
            inventory.save()

        order.status      = Order.STATUS_CANCELLED
        order.cancelled_at = timezone.now()
        order.save()

        send_notification(order.user, 'order_cancelled', order.id)

        return Response({'message': 'Order cancelled successfully. Inventory restored.'}, status=status.HTTP_200_OK)

    @extend_schema(
        summary='Track Order',
        responses={200: OpenApiResponse(description='Tracking info returned.')},
        tags=['orders']
    )
    @action(detail=True, methods=['get'], url_path='track', permission_classes=[IsAuthenticatedCustomer])
    def track(self, request, pk=None):
        order = self.get_object()

        if request.user.role != 'admin' and order.user != request.user:
            return Response({'error': 'You can only track your own orders.'}, status=status.HTTP_403_FORBIDDEN)

        timeline = [{'stage': 'Order Placed', 'status': 'completed', 'timestamp': order.created_at}]

        stages = [
            ('processing', 'Processing', order.processed_at),
            ('shipped',    'Shipped',    order.shipped_at),
            ('completed',  'Delivered',  order.completed_at),
            ('cancelled',  'Cancelled',  order.cancelled_at),
        ]

        for stage_key, stage_label, timestamp in stages:
            if timestamp:
                timeline.append({'stage': stage_label, 'status': 'completed', 'timestamp': timestamp})
            elif order.status not in [Order.STATUS_CANCELLED, Order.STATUS_COMPLETED]:
                if stage_key != 'cancelled':
                    timeline.append({'stage': stage_label, 'status': 'pending', 'timestamp': None})

        return Response({
            'order_id':       order.id,
            'customer_name':  order.customer_name,
            'current_status': order.status,
            'delivery_city':  order.delivery_city,
            'total_price':    str(order.total_price),
            'payment_method': order.payment_method,
            'payment_status': order.payment_status,
            'timeline':       timeline,
        }, status=status.HTTP_200_OK)

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
            OpenApiExample(name='Update Status Example', value={'status': 'processing'}, request_only=True)
        ]
    )
    @action(detail=True, methods=['patch'], url_path='update-status', permission_classes=[IsAdminRole])
    def update_status(self, request, pk=None):
        order      = self.get_object()
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
                {'error': f'Cannot move from "{order.status}" to "{new_status}". Allowed: {allowed}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        timestamp_map = {
            Order.STATUS_PROCESSING: 'processed_at',
            Order.STATUS_SHIPPED:    'shipped_at',
            Order.STATUS_COMPLETED:  'completed_at',
            Order.STATUS_CANCELLED:  'cancelled_at',
        }

        order.status = new_status
        timestamp_field = timestamp_map.get(new_status)
        if timestamp_field:
            setattr(order, timestamp_field, timezone.now())
        order.save()

        STATUS_NOTIFICATION_MAP = {
            Order.STATUS_PROCESSING: 'order_processing',
            Order.STATUS_SHIPPED:    'order_shipped',
            Order.STATUS_COMPLETED:  'order_completed',
            Order.STATUS_CANCELLED:  'order_cancelled',
        }
        notification_type = STATUS_NOTIFICATION_MAP.get(new_status)
        if notification_type:
            send_notification(order.user, notification_type, order.id)

        return Response({
            'message':    f'Order status updated to "{new_status}".',
            'order_id':   order.id,
            'status':     order.status,
            'updated_at': order.updated_at,
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary='Confirm eSewa Payment',
        responses={
            200: OpenApiResponse(description='Payment confirmed successfully.'),
            400: OpenApiResponse(description='Invalid payment data.'),
        },
        tags=['orders']
    )
    @action(detail=True, methods=['post'], url_path='confirm-payment', permission_classes=[IsAuthenticatedCustomer])
    def confirm_payment(self, request, pk=None):
        order = self.get_object()

        if request.user.role != 'admin' and order.user != request.user:
            return Response({'error': 'You can only confirm payment for your own orders.'}, status=status.HTTP_403_FORBIDDEN)

        if order.payment_method != Order.PAYMENT_METHOD_ESEWA:
            return Response({'error': 'This order is not for eSewa payment.'}, status=status.HTTP_400_BAD_REQUEST)

        if order.payment_status == 'paid':
            return Response({'error': 'Payment already confirmed for this order.'}, status=status.HTTP_400_BAD_REQUEST)

        transaction_id = request.data.get('transaction_id')
        if not transaction_id:
            return Response({'error': 'Transaction ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        order.payment_status         = 'paid'
        order.payment_transaction_id = transaction_id
        order.paid_at                = timezone.now()
        order.save()

        if order.status == Order.STATUS_PENDING:
            order.status       = Order.STATUS_PROCESSING
            order.processed_at = timezone.now()
            order.save()

        return Response({
            'message':        'Payment confirmed successfully!',
            'order_id':       order.id,
            'payment_status': order.payment_status,
            'transaction_id': order.payment_transaction_id,
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary='Get Payment QR Code',
        responses={
            200: OpenApiResponse(description='QR code generated successfully.'),
            400: OpenApiResponse(description='Order not eligible for QR payment.'),
        },
        tags=['orders']
    )
    @action(detail=True, methods=['get'], url_path='payment-qr', permission_classes=[IsAuthenticatedCustomer])
    def payment_qr(self, request, pk=None):
        order = self.get_object()

        if request.user.role != 'admin' and order.user != request.user:
            return Response({'error': 'You can only access your own orders.'}, status=status.HTTP_403_FORBIDDEN)

        if order.payment_method != Order.PAYMENT_METHOD_ESEWA:
            return Response({'error': 'This order is not for eSewa payment.'}, status=status.HTTP_400_BAD_REQUEST)

        if order.payment_status == 'paid':
            return Response({'error': 'This order has already been paid.'}, status=status.HTTP_400_BAD_REQUEST)

        if order.status == Order.STATUS_CANCELLED:
            return Response({'error': 'Cannot generate QR for a cancelled order.'}, status=status.HTTP_400_BAD_REQUEST)

        qr_data = self._generate_payment_qr(order)

        return Response({
            'order_id':       order.id,
            'customer_name':  order.customer_name,
            'amount':         str(order.total_price),
            'currency':       'NPR',
            'payment_method': 'eSewa',
            'payment_status': order.payment_status,
            'qr_code':        qr_data['qr_code'],
            'esewa_url':      qr_data['esewa_url'],
            'instructions': (
                f'1. Open eSewa app\n'
                f'2. Scan the QR code\n'
                f'3. Confirm payment of NPR {order.total_price}\n'
                f'4. After payment, call confirm-payment endpoint with transaction ID'
            ),
        }, status=status.HTTP_200_OK)