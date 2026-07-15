from decimal import Decimal
from urllib import response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from django.db import transaction
from notifications.utils import send_notification
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets, serializers
from rest_framework.decorators import APIView, APIView, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from config.permissions import IsAuthenticatedCustomer, IsAdminRole
from tenants.mixins import TenantViewMixin
from inventory.models import Inventory
from products.models import Product

from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from django.http import FileResponse, FileResponse, HttpResponse
from .services import InvoiceService
from .pdf_generator import InvoicePDFGenerator

from inventory.services.warehouse_allocator import allocate_warehouse

from .models import Invoice, Invoice, Order, OrderItem, OrderPrescription
from .serializers import (
    OrderSerializer,
    OrderCustomerSerializer,
    OrderAdminSerializer,
    PrescriptionUploadSerializer,
    PrescriptionReviewSerializer,
    PrescriptionDetailSerializer,
    OrderPrescriptionStatusSerializer,
    get_order_prescription_status,
)

from rest_framework import generics
from .models import Order
from .serializers import OrderCreateSerializer


class OrderCreateAPIView(generics.CreateAPIView):
    serializer_class = OrderCreateSerializer
    queryset = Order.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


# Inline serializers for Swagger docs 
class OrderItemCreateSerializer(serializers.Serializer):
    product  = serializers.IntegerField(help_text='Product ID')
    quantity = serializers.IntegerField(help_text='Quantity', min_value=1)


# UPDATED: Removed delivery fields
class OrderCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(help_text='Customer full name')
    payment_method = serializers.ChoiceField(
        choices=['esewa', 'khalti', 'cod'],
        default='cod',
        help_text='esewa, khalti or cod'
    )
    delivery_city = serializers.CharField(required=False, help_text='Delivery city')
    items = OrderItemCreateSerializer(many=True)


class ConfirmPaymentSerializer(serializers.Serializer):
    transaction_id = serializers.CharField(
        help_text='Transaction ID from eSewa or Khalti app after payment.'
    )


class AdminUpdateOrderSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            Order.STATUS_PENDING,
            Order.STATUS_PROCESSING,
            Order.STATUS_SHIPPED,
            Order.STATUS_COMPLETED,
            Order.STATUS_CANCELLED,
        ],
        required=False,
        help_text='New order status'
    )
    payment_status = serializers.ChoiceField(
        choices=['pending', 'paid', 'failed', 'refunded'],
        required=False,
        help_text='New payment status'
    )


class OrderViewSet(TenantViewMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedCustomer]

    queryset = Order.objects.select_related('user').prefetch_related(
        'items',
        'items__product',
        'items__warehouse',
        'prescription',  # Add prescription relation
        'prescription__reviewed_by',  # Add reviewer relation
    )

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'role', None) == 'admin':
            return qs
        return qs.filter(user=user)

    def get_serializer_class(self):
        if getattr(self.request.user, 'role', None) == 'admin':
            return OrderAdminSerializer
        return OrderCustomerSerializer

    @extend_schema(
        summary='Create Order',
        description=(
            'Create a new order.\n\n'
            '**COD**: Pay on delivery — no extra steps.\n\n'
            '**eSewa**: Pay on eSewa app then call '
            '`/confirm-payment/` with your transaction ID.\n\n'
            '**Khalti**: Pay on Khalti app then call '
            '`/confirm-payment/` with your transaction ID.\n\n'
            '**Prescription**: If any product requires prescription, '
            'the response will include `requires_prescription: true`. '
            'You must then upload the prescription using `/upload-prescription/`.'
        ),
        request=OrderCreateSerializer,
        responses={
            201: OrderCustomerSerializer,
            400: OpenApiResponse(description='Bad request.'),
        },
        tags=['Orders'],
        examples=[
            OpenApiExample(
                'COD Order',
                value={
                    'customer_name': 'Purnima',
                    'payment_method': 'cod',
                    'delivery_city': 'pokhara',
                    'items': [
                        {'product': 1, 'quantity': 2},
                        {'product': 3, 'quantity': 1}
                    ]
                },
                request_only=True,
            ),
            OpenApiExample(
                'eSewa Order',
                value={
                    'customer_name': 'Purnima',
                    'payment_method': 'esewa',
                    'delivery_city': 'kathmandu',
                    'items': [{'product': 2, 'quantity': 1}]
                },
                request_only=True,
            ),
            OpenApiExample(
                'Khalti Order',
                value={
                    'customer_name': 'Purnima',
                    'payment_method': 'khalti',
                    'delivery_city': 'lalitpur',
                    'items': [{'product': 4, 'quantity': 3}]
                },
                request_only=True,
            ),
        ]
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data

        if not data.get("customer_name"):
            return Response(
                {"error": "customer_name is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        items_data = data.get("items") or data.get("create_items", [])
        if not items_data:
            return Response(
                {"error": "At least one item is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_method = data.get("payment_method", Order.PAYMENT_METHOD_COD)
        if payment_method not in [
            Order.PAYMENT_METHOD_ESEWA,
            Order.PAYMENT_METHOD_KHALTI,
            Order.PAYMENT_METHOD_COD,
        ]:
            return Response(
                {"error": 'Invalid payment_method. Must be "esewa", "khalti" or "cod".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Handle delivery city
        delivery_city = data.get("delivery_city", "").strip()
        if not delivery_city:
            try:
                delivery_city = request.user.profile.city or ""
            except Exception:
                delivery_city = ""

        if not delivery_city:
            return Response(
                {"error": "No delivery city set. Provide delivery_city or update your profile city."},
                status=status.HTTP_400_BAD_REQUEST
            )

        vendor_groups = {}

        for item in items_data:
            product_id = item.get("product")
            quantity_val = item.get("quantity", 1)

            if not product_id:
                return Response(
                    {"error": "Each item must have a product ID."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                quantity = int(quantity_val)
            except (ValueError, TypeError):
                return Response(
                    {"error": f"Invalid quantity for product ID {product_id}."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if quantity <= 0:
                return Response(
                    {"error": "Quantity must be greater than 0."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                product = Product.objects.get(
                    id=int(product_id),
                    tenant__is_active=True
                )
            except Product.DoesNotExist:
                return Response(
                    {"error": f"Product with id {product_id} does not exist."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Allocate warehouse without coordinates
            allocation = allocate_warehouse(
                tenant=product.tenant,
                product=product,
                quantity=quantity,
                customer_latitude=None,
                customer_longitude=None,
            )

            if allocation is None:
                return Response(
                    {"error": f'No warehouse has enough stock for "{product.name}".'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            inventory = allocation["inventory"]
            warehouse = allocation["warehouse"]

            if product.quantity < quantity:
                return Response(
                    {"error": f"Insufficient stock for {product.name}."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            tenant_id = product.tenant_id
            unit_price = Decimal(str(product.price))

            if tenant_id not in vendor_groups:
                vendor_groups[tenant_id] = {
                    "tenant": product.tenant,
                    "items": [],
                    "original_amount": Decimal("0.00"),
                }

            vendor_groups[tenant_id]["original_amount"] += unit_price * quantity
            vendor_groups[tenant_id]["items"].append({
                "product": product,
                "warehouse": warehouse,
                "inventory": inventory,
                "quantity": quantity,
                "unit_price": unit_price,
            })

        if not vendor_groups:
            return Response(
                {"error": "No valid order items found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_orders = []

        for group in vendor_groups.values():
            original_amount = group["original_amount"].quantize(Decimal("0.01"))
            discount_amount = Decimal("0.00")
            total_price = original_amount

            try:
                order = Order.objects.create(
                    tenant=group["tenant"],
                    user=request.user,
                    customer_name=data.get("customer_name"),
                    delivery_city=delivery_city,
                    payment_method=payment_method,
                    original_amount=original_amount,
                    discount_amount=discount_amount,
                    total_price=total_price,
                    status=Order.STATUS_PENDING,
                    payment_status=Order.PAYMENT_STATUS_PENDING,
                )
            except ValidationError as e:
                error_msg = e.message_dict if hasattr(e, "message_dict") else str(e)
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )

            for item_data in group["items"]:
                product = item_data["product"]

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    warehouse=item_data["warehouse"],
                    quantity=item_data["quantity"],
                    unit_price=item_data["unit_price"],
                )

                inv = item_data["inventory"]
                inv.quantity -= item_data["quantity"]
                inv.save()

                product.quantity -= item_data["quantity"]
                product.save()

            InvoiceService.create_invoice(order)

            send_notification(
                order=order,
                notification_type="order_placed",
            )

            created_orders.append(order)

        # Serialize response with prescription fields
        serializer = OrderCustomerSerializer(created_orders, many=True)
        
        return Response(
            {
                "message": "Orders created successfully.",
                "orders": serializer.data,
            },
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only admins can update orders.'},
                status=status.HTTP_403_FORBIDDEN
            )

        order = self.get_object()
        old_status = order.status  # Store old status before changes
        new_status = request.data.get('status')
        new_payment_status = request.data.get('payment_status')

        if new_status:
            valid_transitions = {
                Order.STATUS_PENDING:    [Order.STATUS_PROCESSING, Order.STATUS_CANCELLED],
                Order.STATUS_PROCESSING: [Order.STATUS_SHIPPED,    Order.STATUS_CANCELLED],
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
                Order.STATUS_SHIPPED: 'shipped_at',
                Order.STATUS_COMPLETED: 'completed_at',
                Order.STATUS_CANCELLED: 'cancelled_at',
            }
            timestamp_field = timestamp_map.get(new_status)
            if timestamp_field:
                setattr(order, timestamp_field, timezone.now())
            order.status = new_status

        if new_payment_status:
            if order.payment_status == Order.PAYMENT_STATUS_PAID and new_payment_status != Order.PAYMENT_STATUS_PAID:
                return Response(
                    {'error': 'Cannot change payment status once it is "paid".'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if new_payment_status == Order.PAYMENT_STATUS_PAID and order.payment_status != Order.PAYMENT_STATUS_PAID:
                order.paid_at = timezone.now()
            order.payment_status = new_payment_status

        order.save()

        # Send notification if status changed
        if new_status and new_status != old_status:
            notification_map = {
                Order.STATUS_PROCESSING: "order_processing",
                Order.STATUS_SHIPPED: "order_shipped",
                Order.STATUS_COMPLETED: "order_completed",
                Order.STATUS_CANCELLED: "order_cancelled",
            }

            notification_type = notification_map.get(new_status)

            if notification_type:
                send_notification(
                    order=order,
                    notification_type=notification_type,
                )

        return Response(
            OrderAdminSerializer(order).data,
            status=status.HTTP_200_OK
        )

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only admins can delete orders.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary='Cancel Order',
        description='Cancel a pending or processing order. Inventory is restored.',
        responses={
            200: OpenApiResponse(description='Cancelled successfully.'),
            400: OpenApiResponse(description='Cannot cancel.'),
            403: OpenApiResponse(description='Not your order.'),
        },
        tags=['Orders']
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

        if order.status == Order.STATUS_COMPLETED:
            return Response(
                {'error': 'Cannot cancel a completed order.'},
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

        # Send cancellation notification
        send_notification(
            order=order,
            notification_type="order_cancelled",
        )

        return Response(
            {'message': 'Order cancelled successfully. Inventory restored.'},
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary='Track Order',
        description='Get full timeline of order stages.',
        responses={200: OpenApiResponse(description='Tracking info.')},
        tags=['Orders']
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

        timeline = [{
            'stage': 'Order Placed',
            'status': 'completed',
            'timestamp': order.created_at
        }]

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
                    'timestamp': timestamp
                })
            elif order.status not in [Order.STATUS_CANCELLED, Order.STATUS_COMPLETED]:
                if stage_key != 'cancelled':
                    timeline.append({
                        'stage': stage_label,
                        'status': 'pending',
                        'timestamp': None
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
        summary='Confirm eSewa / Khalti Payment',
        description=(
            'After paying on eSewa or Khalti app, '
            'submit your transaction ID to confirm payment.\n\n'
            'Not needed for COD orders.'
        ),
        request=ConfirmPaymentSerializer,
        responses={
            200: OpenApiResponse(description='Payment confirmed.'),
            400: OpenApiResponse(description='Invalid data.'),
            403: OpenApiResponse(description='Not your order.'),
        },
        tags=['Orders'],
        examples=[
            OpenApiExample(
                'Confirm eSewa Payment',
                value={'transaction_id': 'ESEWA-TXN-123456789'},
                request_only=True,
            ),
            OpenApiExample(
                'Confirm Khalti Payment',
                value={'transaction_id': 'KHALTI-TXN-987654321'},
                request_only=True,
            ),
        ]
    )
    @action(
        detail=True,
        methods=['post'],
        url_path='confirm-payment',
        permission_classes=[IsAuthenticatedCustomer]
    )
    def confirm_payment(self, request, pk=None):
        order = self.get_object()

        if request.user.role != 'admin' and order.user != request.user:
            return Response(
                {'error': 'You can only confirm payment for your own orders.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if order.payment_method == Order.PAYMENT_METHOD_COD:
            return Response(
                {'error': 'This order uses Cash on Delivery. No payment confirmation needed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if order.payment_status == Order.PAYMENT_STATUS_PAID:
            return Response(
                {'error': 'Payment already confirmed for this order.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if order.status == Order.STATUS_CANCELLED:
            return Response(
                {'error': 'Cannot confirm payment for a cancelled order.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        transaction_id = request.data.get('transaction_id')
        if not transaction_id:
            return Response(
                {'error': 'transaction_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Order.objects.filter(payment_transaction_id=transaction_id).exclude(id=order.id).exists():
            return Response(
                {'error': 'This transaction ID has already been used.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Store old status before any changes
        old_status = order.status

        order.payment_status = Order.PAYMENT_STATUS_PAID
        order.payment_transaction_id = transaction_id
        order.paid_at = timezone.now()

        # Auto-transition from pending to processing on payment confirmation
        if order.status == Order.STATUS_PENDING:
            order.status = Order.STATUS_PROCESSING
            order.processed_at = timezone.now()

        order.save()

        # Send notification only if status changed to processing
        if old_status != order.status and order.status == Order.STATUS_PROCESSING:
            send_notification(
                order=order,
                notification_type="order_processing",
            )

        payment_label = 'eSewa' if order.payment_method == Order.PAYMENT_METHOD_ESEWA else 'Khalti'

        return Response(
            {
                'message': f'{payment_label} payment confirmed! Your order is now being processed.',
                'order_id': order.id,
                'payment_status': order.payment_status,
                'order_status': order.status,
                'transaction_id': order.payment_transaction_id,
                'paid_at': order.paid_at,
            },
            status=status.HTTP_200_OK
        )

    # ==================== PRESCRIPTION ENDPOINTS ====================

    @extend_schema(
        summary='Upload Prescription',
        description=(
            'Upload a prescription image for an order that requires a prescription.\n\n'
            '**Requirements:**\n'
            '- Only the order owner or admin can upload\n'
            '- Image must be in JPEG, PNG, or GIF format\n'
            '- Image size must not exceed 5MB\n'
            '- Only one prescription per order is allowed\n'
            '- Order must be in pending or processing status'
        ),
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'image': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Prescription image file (JPEG, PNG, GIF)'
                    }
                },
                'required': ['image']
            }
        },
        responses={
            201: OpenApiResponse(
                description='Prescription uploaded successfully.',
                response=PrescriptionDetailSerializer
            ),
            400: OpenApiResponse(description='Invalid data.'),
            403: OpenApiResponse(description='Permission denied.'),
            404: OpenApiResponse(description='Order not found.'),
        },
        tags=['Prescriptions']
    )
    @action(
        detail=True,
        methods=['post'],
        url_path='upload-prescription',
        permission_classes=[IsAuthenticated]
    )
    def upload_prescription(self, request, pk=None):
        """
        Upload a prescription for an order.
        """
        order = self.get_object()
        user = request.user

        # Check permission: order owner or admin
        if not (user == order.user or getattr(user, 'role', None) == 'admin'):
            return Response(
                {"error": "You don't have permission to upload a prescription for this order."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if order requires prescription
        requires_prescription = order.items.filter(product__requires_prescription=True).exists()
        if not requires_prescription:
            return Response(
                {"error": "This order does not require a prescription."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if prescription already exists
        if hasattr(order, 'prescription'):
            return Response(
                {"error": f"Prescription already uploaded. Status: {order.prescription.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if order can accept prescription (not shipped/completed/cancelled)
        if order.status in [Order.STATUS_SHIPPED, Order.STATUS_COMPLETED, Order.STATUS_CANCELLED]:
            return Response(
                {"error": f"Cannot upload prescription for order with status: {order.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate and upload prescription
        serializer = PrescriptionUploadSerializer(data=request.data)
        if serializer.is_valid():
            prescription = OrderPrescription.objects.create(
                order=order,
                image=serializer.validated_data['image']
            )
            
            # Refresh order to include prescription
            order.refresh_from_db()
            
            return Response(
                {
                    "message": "Prescription uploaded successfully.",
                    "prescription": PrescriptionDetailSerializer(prescription).data,
                    "order": OrderCustomerSerializer(order).data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary='Review Prescription',
        description=(
            'Approve or reject a prescription (Admin/Vendor only).\n\n'
            '**Requirements:**\n'
            '- Only admins or vendors can review\n'
            '- Prescription must be in pending status\n'
            '- Cannot re-review an already reviewed prescription'
        ),
        request=PrescriptionReviewSerializer,
        responses={
            200: OpenApiResponse(
                description='Prescription reviewed successfully.',
                response=PrescriptionDetailSerializer
            ),
            400: OpenApiResponse(description='Invalid data.'),
            403: OpenApiResponse(description='Permission denied.'),
            404: OpenApiResponse(description='Order or prescription not found.'),
        },
        tags=['Prescriptions']
    )
    @action(
        detail=True,
        methods=['patch'],
        url_path='review-prescription',
        permission_classes=[IsAuthenticated]
    )
    def review_prescription(self, request, pk=None):
        """
        Review a prescription (approve or reject).
        """
        order = self.get_object()
        user = request.user

        # Check permission: admin or vendor
        if not (getattr(user, 'role', None) == 'admin' or hasattr(user, 'vendor_profile')):
            return Response(
                {"error": "Only admins or vendors can review prescriptions."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if prescription exists
        if not hasattr(order, 'prescription'):
            return Response(
                {"error": "No prescription found for this order."},
                status=status.HTTP_404_NOT_FOUND
            )

        prescription = order.prescription

        # Don't allow re-review
        if prescription.status != OrderPrescription.Status.PENDING:
            return Response(
                {"error": f"Prescription already {prescription.status}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate and review
        serializer = PrescriptionReviewSerializer(data=request.data)
        if serializer.is_valid():
            status_value = serializer.validated_data['status']
            notes = serializer.validated_data.get('notes', '')

            if status_value == 'approved':
                prescription.approve(user)
                message = "Prescription approved successfully."
            else:
                prescription.reject(user)
                message = "Prescription rejected successfully."

            return Response(
                {
                    "message": message,
                    "prescription": PrescriptionDetailSerializer(prescription).data,
                    "order": OrderCustomerSerializer(order).data
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary='Get Prescription Status',
        description=(
            'Get the prescription status for an order.\n\n'
            'Returns:\n'
            '- Whether prescription is required\n'
            '- Current status (pending/approved/rejected/not_uploaded)\n'
            '- Whether the user can upload or review'
        ),
        responses={
            200: OpenApiResponse(
                description='Prescription status retrieved.',
                response=OrderPrescriptionStatusSerializer
            ),
            403: OpenApiResponse(description='Permission denied.'),
            404: OpenApiResponse(description='Order not found.'),
        },
        tags=['Prescriptions']
    )
    @action(
        detail=True,
        methods=['get'],
        url_path='prescription-status',
        permission_classes=[IsAuthenticated]
    )
    def prescription_status(self, request, pk=None):
        """
        Get prescription status for an order.
        """
        order = self.get_object()
        user = request.user

        # Check permission: order owner, admin, or vendor
        if not (user == order.user or getattr(user, 'role', None) == 'admin' or hasattr(user, 'vendor_profile')):
            return Response(
                {"error": "You don't have permission to view this order's prescription status."},
                status=status.HTTP_403_FORBIDDEN
            )

        status_data = get_order_prescription_status(order)
        
        # Add user permissions to response
        status_data['can_upload'] = (
            status_data['can_upload'] and 
            (user == order.user or getattr(user, 'role', None) == 'admin')
        )
        status_data['can_review'] = (
            status_data['can_review'] and 
            (getattr(user, 'role', None) == 'admin' or hasattr(user, 'vendor_profile'))
        )

        return Response(status_data, status=status.HTTP_200_OK)

    @extend_schema(
        summary='Get Prescription Details',
        description=(
            'Get detailed prescription information including the image URL.\n\n'
            'Only accessible to order owner, admin, or vendor.'
        ),
        responses={
            200: OpenApiResponse(
                description='Prescription details retrieved.',
                response=PrescriptionDetailSerializer
            ),
            403: OpenApiResponse(description='Permission denied.'),
            404: OpenApiResponse(description='Order or prescription not found.'),
        },
        tags=['Prescriptions']
    )
    @action(
        detail=True,
        methods=['get'],
        url_path='prescription',
        permission_classes=[IsAuthenticated]
    )
    def get_prescription(self, request, pk=None):
        """
        Get prescription details for an order.
        """
        order = self.get_object()
        user = request.user

        # Check permission: order owner, admin, or vendor
        if not (user == order.user or getattr(user, 'role', None) == 'admin' or hasattr(user, 'vendor_profile')):
            return Response(
                {"error": "You don't have permission to view this order's prescription."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if prescription exists
        if not hasattr(order, 'prescription'):
            return Response(
                {"error": "No prescription found for this order."},
                status=status.HTTP_404_NOT_FOUND
            )

        prescription = order.prescription
        serializer = PrescriptionDetailSerializer(prescription)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary='Delete Prescription',
        description=(
            'Delete a prescription (Admin only).\n\n'
            'Only admins can delete prescriptions.'
        ),
        responses={
            200: OpenApiResponse(description='Prescription deleted successfully.'),
            403: OpenApiResponse(description='Permission denied.'),
            404: OpenApiResponse(description='Order or prescription not found.'),
        },
        tags=['Prescriptions']
    )
    @action(
        detail=True,
        methods=['delete'],
        url_path='prescription',
        permission_classes=[IsAuthenticated]
    )
    def delete_prescription(self, request, pk=None):
        """
        Delete a prescription (admin only).
        """
        order = self.get_object()
        user = request.user

        # Only admin can delete
        if getattr(user, 'role', None) != 'admin':
            return Response(
                {"error": "Only admins can delete prescriptions."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if prescription exists
        if not hasattr(order, 'prescription'):
            return Response(
                {"error": "No prescription found for this order."},
                status=status.HTTP_404_NOT_FOUND
            )

        prescription = order.prescription
        prescription.delete()

        return Response(
            {"message": "Prescription deleted successfully."},
            status=status.HTTP_200_OK
        )


class VendorOrderViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderAdminSerializer

    queryset = Order.objects.select_related(
        "tenant",
        "user"
    ).prefetch_related(
        "items",
        "items__product",
        "items__warehouse",
        "prescription",  # Add prescription relation
        "prescription__reviewed_by",
    )

    def get_queryset(self):
        tenant = self.get_tenant()
        return self.queryset.filter(tenant=tenant).order_by("-created_at")

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        order = self.get_object()

        if order.status != Order.STATUS_PENDING:
            return Response(
                {"error": "Only pending orders can be moved to processing."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = Order.STATUS_PROCESSING
        order.processed_at = timezone.now()
        order.save(update_fields=[
            "status",
            "processed_at",
            "updated_at",
        ])

        InvoiceService.create_invoice(order)

        # Send processing notification
        send_notification(
            order=order,
            notification_type="order_processing",
        )

        return Response({
            "message": "Order moved to processing.",
            "order_id": order.id,
            "status": order.status,
        })

    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        order = self.get_object()

        if order.status != Order.STATUS_PROCESSING:
            return Response(
                {"error": "Only processing orders can be shipped."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = Order.STATUS_SHIPPED
        order.shipped_at = timezone.now()
        order.save()

        # Send shipped notification
        send_notification(
            order=order,
            notification_type="order_shipped",
        )

        return Response({
            "message": "Order shipped.",
            "order_id": order.id,
            "status": order.status
        })

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        order = self.get_object()

        if order.status != Order.STATUS_SHIPPED:
            return Response(
                {"error": "Only shipped orders can be completed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = Order.STATUS_COMPLETED
        order.completed_at = timezone.now()
        order.save()

        # Send completed notification
        send_notification(
            order=order,
            notification_type="order_completed",
        )

        return Response({
            "message": "Order completed.",
            "order_id": order.id,
            "status": order.status
        })

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()

        if order.status == Order.STATUS_CANCELLED:
            return Response(
                {"error": "Order is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if order.status in [Order.STATUS_SHIPPED, Order.STATUS_COMPLETED]:
            return Response(
                {"error": f"Cannot cancel order with status: {order.status}"},
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

        # Send cancellation notification
        send_notification(
            order=order,
            notification_type="order_cancelled",
        )

        return Response({
            "message": "Order cancelled successfully.",
            "order_id": order.id,
            "status": order.status
        })


class InvoiceDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        invoice = Invoice.objects.get(pk=pk)
        pdf = InvoicePDFGenerator.generate(invoice)
        return FileResponse(
            pdf,
            as_attachment=True,
            filename=f"{invoice.invoice_number}.pdf"
        )


# ==================== ADMIN VIEWS FOR PRESCRIPTIONS ====================

from rest_framework import generics
from .models import OrderPrescription
from .serializers import PrescriptionDetailSerializer


class AdminPrescriptionListView(generics.ListAPIView):
    """
    Admin view to list all prescriptions with filtering options.
    """
    permission_classes = [IsAdminRole]
    serializer_class = PrescriptionDetailSerializer
    queryset = OrderPrescription.objects.select_related(
        'order',
        'order__user',
        'reviewed_by'
    ).order_by('-uploaded_at')

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        from_date = self.request.query_params.get('from_date')
        if from_date:
            queryset = queryset.filter(uploaded_at__gte=from_date)
        
        to_date = self.request.query_params.get('to_date')
        if to_date:
            queryset = queryset.filter(uploaded_at__lte=to_date)
        
        # Filter by tenant
        tenant = self.request.tenant
        if tenant:
            queryset = queryset.filter(order__tenant=tenant)
        
        return queryset


class AdminPrescriptionReviewView(generics.UpdateAPIView):
    """
    Admin view to review a prescription.
    """
    permission_classes = [IsAdminRole]
    serializer_class = PrescriptionReviewSerializer
    queryset = OrderPrescription.objects.all()

    def update(self, request, *args, **kwargs):
        prescription = self.get_object()
        
        if prescription.status != OrderPrescription.Status.PENDING:
            return Response(
                {"error": f"Prescription already {prescription.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            status_value = serializer.validated_data['status']
            
            if status_value == 'approved':
                prescription.approve(request.user)
            else:
                prescription.reject(request.user)
            
            return Response({
                "message": f"Prescription {status_value} successfully",
                "prescription": PrescriptionDetailSerializer(prescription).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)