from decimal import Decimal
from urllib import response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from rest_framework import status, viewsets, serializers
from rest_framework.decorators import APIView, APIView, action
from rest_framework.response import Response

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

from .models import Invoice, Invoice, Order, OrderItem
from .serializers import (
    OrderSerializer,
    OrderCustomerSerializer,
    OrderAdminSerializer,
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


# UPDATED: added khalti to choices; delivery_city auto-filled from profile
class OrderCreateSerializer(serializers.Serializer):
    customer_name  = serializers.CharField(help_text='Customer full name')
    payment_method = serializers.ChoiceField(
        choices=['esewa', 'khalti', 'cod'],
        default='cod',
        help_text='esewa, khalti or cod'
    )
    items = OrderItemCreateSerializer(many=True)


class ConfirmPaymentSerializer(serializers.Serializer):
    transaction_id = serializers.CharField(
        # mentions both eSewa and Khalti
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


# ###ViewSet 

class OrderViewSet(TenantViewMixin, viewsets.ModelViewSet):

    permission_classes = [IsAuthenticatedCustomer]

    queryset = Order.objects.select_related('user').prefetch_related(
        'items',
        'items__product',
        'items__warehou' \
        'se',
    )


    def get_queryset(self):
        qs = super().get_queryset()  # applies TenantViewMixin tenant filter
        user = self.request.user
        if getattr(user, 'role', None) == 'admin':
            return qs
        return qs.filter(user=user)

    def get_serializer_class(self):
        if getattr(self.request.user, 'role', None) == 'admin':
            return OrderAdminSerializer
        return OrderCustomerSerializer

    # Create Order 

    @extend_schema(
        summary='Create Order',
        ##### description now mentions Khalti
        description=(
            'Create a new order.\n\n'
            '**COD**: Pay on delivery — no extra steps.\n\n'
            '**eSewa**: Pay on eSewa app then call '
            '`/confirm-payment/` with your transaction ID.\n\n'
            '**Khalti**: Pay on Khalti app then call '       #  NEW
            '`/confirm-payment/` with your transaction ID.'  # NEW
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
                    'customer_name':  'Purnima',
                    'payment_method': 'cod',
                    'delivery_city':'pokhara',
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
                    'customer_name':  'Purnima',
                    'payment_method': 'esewa',
                    'delivery_city':'pokhara',
                    'items': [{'product': 2, 'quantity': 1}]
                },
                request_only=True,
            ),
            OpenApiExample(
                'Khalti Order',
                value={
                    'customer_name':  'Purnima',
                    'payment_method': 'khalti',
                    'delivery_city':'pokhara',
                    'items': [{'product': 4, 'quantity': 3}]
                },
                request_only=True,
            ),
        ]
    )
#     @extend_schema(
#     parameters=[
#         OpenApiParameter(
#             name="X-Tenant-Slug",
#             type=str,
#             location=OpenApiParameter.HEADER,
#             required=True,
#             description="Vendor tenant slug. Example: glow-beauty-store-123",
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
            allocation = allocate_warehouse(
                tenant=product.tenant,
                product=product,
                quantity=quantity,
                customer_latitude=float(data["delivery_latitude"]),
                customer_longitude=float(data["delivery_longitude"]),
            )

            if allocation is None:
                return Response(
                    {
                        "error": f'No warehouse has enough stock for "{product.name}".'
                    },
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

                delivery_address=data.get("delivery_address"),
                delivery_latitude=data.get("delivery_latitude"),
                delivery_longitude=data.get("delivery_longitude"),

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

            created_orders.append(order)

        return Response(
            {
                "message": "Orders created successfully.",
                "orders": OrderCustomerSerializer(created_orders, many=True).data,
            },
            status=status.HTTP_201_CREATED
    )
    def update(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only admins can update orders.'},
                status=status.HTTP_403_FORBIDDEN
            )

        order              = self.get_object()
        new_status         = request.data.get('status')
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
                    {
                        'error': (
                            f'Cannot move from "{order.status}" to "{new_status}". '
                            f'Allowed: {allowed}'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            timestamp_map = {
                Order.STATUS_PROCESSING: 'processed_at',
                Order.STATUS_SHIPPED:    'shipped_at',
                Order.STATUS_COMPLETED:  'completed_at',
                Order.STATUS_CANCELLED:  'cancelled_at',
            }
            timestamp_field = timestamp_map.get(new_status)
            if timestamp_field:
                setattr(order, timestamp_field, timezone.now())
            order.status = new_status

        ##### UPDATED: uses constants instead of raw strings
        if new_payment_status:
            if (
                order.payment_status == Order.PAYMENT_STATUS_PAID and  
                new_payment_status != Order.PAYMENT_STATUS_PAID        
            ):
                return Response(
                    {'error': 'Cannot change payment status once it is "paid".'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if (
                new_payment_status == Order.PAYMENT_STATUS_PAID and   
                order.payment_status != Order.PAYMENT_STATUS_PAID      
            ):
                order.paid_at = timezone.now()
            order.payment_status = new_payment_status

        order.save()

        return Response(
            OrderAdminSerializer(order).data,
            status=status.HTTP_200_OK
        )

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    #### Delete Order (Admin) 

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only admins can delete orders.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    # ##Cancel Order 

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

        # ## NEW: added check for completed orders
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

        order.status       = Order.STATUS_CANCELLED
        order.cancelled_at = timezone.now()
        order.save()

        return Response(
            {'message': 'Order cancelled successfully. Inventory restored.'},
            status=status.HTTP_200_OK
        )

    # Track Order 

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
            'stage':     'Order Placed',
            'status':    'completed',
            'timestamp': order.created_at
        }]

        stages = [
            ('processing', 'Processing', order.processed_at),
            ('shipped',    'Shipped',    order.shipped_at),
            ('completed',  'Delivered',  order.completed_at),
            ('cancelled',  'Cancelled',  order.cancelled_at),
        ]

        for stage_key, stage_label, timestamp in stages:
            if timestamp:
                timeline.append({
                    'stage':     stage_label,
                    'status':    'completed',
                    'timestamp': timestamp
                })
            elif order.status not in [
                Order.STATUS_CANCELLED,
                Order.STATUS_COMPLETED,
            ]:
                if stage_key != 'cancelled':
                    timeline.append({
                        'stage':     stage_label,
                        'status':    'pending',
                        'timestamp': None
                    })

        return Response(
            {
                'order_id':       order.id,
                'customer_name':  order.customer_name,
                'current_status': order.status,
                'delivery_city':  order.delivery_city,
                'total_price':    str(order.total_price),
                'payment_method': order.payment_method,
                'payment_status': order.payment_status,
                'timeline':       timeline,
            },
            status=status.HTTP_200_OK
        )

    # Confirm Payment (eSewa / Khalti) 

    @extend_schema(
        #UPDATED: title mentions both eSewa and Khalti
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
            # NEW: added Khalti 
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

        #  UPDATED: now checks COD instead of eSewa
        # (allows both eSewa and Khalti to confirm)
        if order.payment_method == Order.PAYMENT_METHOD_COD:
            return Response(
                {'error': 'This order uses Cash on Delivery. No payment confirmation needed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # UPDATED: uses constant
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

        if Order.objects.filter(
            payment_transaction_id=transaction_id
        ).exclude(id=order.id).exists():
            return Response(
                {'error': 'This transaction ID has already been used.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # UPDATED: uses constants
        order.payment_status         = Order.PAYMENT_STATUS_PAID
        order.payment_transaction_id = transaction_id
        order.paid_at                = timezone.now()

        if order.status == Order.STATUS_PENDING:
            order.status       = Order.STATUS_PROCESSING
            order.processed_at = timezone.now()

        order.save()

        #UPDATED: shows correct payment label for eSewa or Khalti
        payment_label = (
            'eSewa'
            if order.payment_method == Order.PAYMENT_METHOD_ESEWA
            else 'Khalti'
        )

        return Response(
            {
                'message':        f'{payment_label} payment confirmed! Your order is now being processed.',
                'order_id':       order.id,
                'payment_status': order.payment_status,
                'order_status':   order.status,
                'transaction_id': order.payment_transaction_id,
                'paid_at':        order.paid_at,
            },
            status=status.HTTP_200_OK
        )
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from tenants.mixins import TenantViewMixin


class VendorOrderViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderAdminSerializer

    queryset = Order.objects.select_related(
        "tenant",
        "user"
    ).prefetch_related(
        "items",
        "items__product",
        "items__warehouse"
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
        order.save()

        InvoiceService.create_invoice(order)

        return Response({
            "message": "Order moved to processing.",
            "order_id": order.id,
            "status": order.status
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

        return Response({
            "message": "Order completed.",
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

    