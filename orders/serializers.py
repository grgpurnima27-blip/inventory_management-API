# orders/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Order, OrderItem, OrderPrescription, Delivery  # Removed Payment
from products.models import Product
from coupons.models import Coupon
from decimal import Decimal
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for order items with additional computed fields.
    """
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        source='unit_price', 
        read_only=True
    )
    product_image = serializers.SerializerMethodField()
    product_requires_prescription = serializers.BooleanField(
        source='product.requires_prescription', 
        read_only=True
    )
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True, allow_null=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 
            'product', 
            'product_name', 
            'product_price',
            'product_image',
            'product_requires_prescription',
            'warehouse',
            'warehouse_name',
            'quantity', 
            'unit_price', 
            'total_price'
        ]
    
    def get_product_image(self, obj):
        """Get the primary image URL for the product."""
        if obj.product and hasattr(obj.product, 'images') and obj.product.images.exists():
            return obj.product.images.first().image.url
        return None
    
    def to_representation(self, instance):
        """Convert Decimal to float for JSON serialization."""
        data = super().to_representation(instance)
        # Convert Decimal fields to float for JSON
        if 'unit_price' in data and data['unit_price'] is not None:
            data['unit_price'] = float(data['unit_price'])
        if 'total_price' in data and data['total_price'] is not None:
            data['total_price'] = float(data['total_price'])
        if 'product_price' in data and data['product_price'] is not None:
            data['product_price'] = float(data['product_price'])
        return data


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for orders with detailed information.
    """
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    total_items = serializers.IntegerField(source='items.count', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    order_status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    # New computed field for prescription requirement
    requires_prescription = serializers.SerializerMethodField()
    
    # Prescription-related fields (read-only, for display)
    prescription_status = serializers.SerializerMethodField()
    prescription_image = serializers.SerializerMethodField()
    prescription_uploaded_at = serializers.SerializerMethodField()
    prescription_reviewed_by = serializers.SerializerMethodField()
    prescription_reviewed_at = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'tenant',
            'tenant_name',
            'user',
            'user_email',
            'user_full_name',
            'customer_name',
            'items',
            'total_items',
            'delivery_city',
            'delivery_address',
            'delivery_charge',
            'payment_method',
            'payment_method_display',
            'payment_status',
            'payment_status_display',
            'payment_transaction_id',
            'status',
            'order_status_display',
            'original_amount',
            'discount_amount',
            'total_price',
            'notes',
            'requires_prescription',  # New computed field
            'prescription_status',    # New field
            'prescription_image',     # New field
            'prescription_uploaded_at', # New field
            'prescription_reviewed_by', # New field
            'prescription_reviewed_at', # New field
            'created_at',
            'updated_at',
            'paid_at',
            'processed_at',
            'shipped_at',
            'completed_at',
            'cancelled_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 
            'user', 'tenant', 'paid_at', 'processed_at', 
            'shipped_at', 'completed_at', 'cancelled_at'
        ]
    
    def get_user_full_name(self, obj):
        """Get user's full name."""
        if obj.user:
            if hasattr(obj.user, 'get_full_name'):
                return obj.user.get_full_name() or obj.user.email
            return obj.user.email
        return None
    
    def get_requires_prescription(self, obj):
        """
        Check if any item in the order requires a prescription.
        """
        if hasattr(obj, 'items'):
            return obj.items.filter(product__requires_prescription=True).exists()
        return False
    
    def get_prescription_status(self, obj):
        """
        Get the prescription status for this order.
        """
        if hasattr(obj, 'prescription'):
            return obj.prescription.status
        return None
    
    def get_prescription_image(self, obj):
        """
        Get the prescription image URL if available.
        """
        if hasattr(obj, 'prescription') and obj.prescription.image:
            try:
                return obj.prescription.image.url
            except:
                return None
        return None
    
    def get_prescription_uploaded_at(self, obj):
        """
        Get prescription upload timestamp.
        """
        if hasattr(obj, 'prescription'):
            return obj.prescription.uploaded_at
        return None
    
    def get_prescription_reviewed_by(self, obj):
        """
        Get who reviewed the prescription.
        """
        if hasattr(obj, 'prescription') and obj.prescription.reviewed_by:
            return obj.prescription.reviewed_by.email
        return None
    
    def get_prescription_reviewed_at(self, obj):
        """
        Get prescription review timestamp.
        """
        if hasattr(obj, 'prescription'):
            return obj.prescription.reviewed_at
        return None
    
    def to_representation(self, instance):
        """Convert Decimal to float for JSON serialization."""
        data = super().to_representation(instance)
        # Convert Decimal fields to float for JSON
        decimal_fields = [
            'delivery_charge', 'original_amount', 'discount_amount',
            'total_price'
        ]
        for field in decimal_fields:
            if field in data and data[field] is not None:
                try:
                    data[field] = float(data[field])
                except (ValueError, TypeError):
                    pass
        return data


class OrderCustomerSerializer(OrderSerializer):
    """
    Customer-facing order serializer with limited fields.
    """
    class Meta(OrderSerializer.Meta):
        fields = [
            'id',
            'customer_name',
            'items',
            'total_items',
            'delivery_city',
            'delivery_address',
            'payment_method',
            'payment_method_display',
            'payment_status',
            'payment_status_display',
            'status',
            'order_status_display',
            'total_price',
            'requires_prescription',
            'prescription_status',
            'prescription_image',
            'prescription_uploaded_at',
            'prescription_reviewed_by',
            'prescription_reviewed_at',
            'created_at',
            'updated_at',
            'paid_at',
            'processed_at',
            'shipped_at',
            'completed_at',
            'cancelled_at'
        ]


class OrderAdminSerializer(OrderSerializer):
    """
    Admin-facing order serializer with all fields.
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + [
            'user_email',
            'user_full_name',
            'tenant_name',
        ]


class OrderCreateItemSerializer(serializers.Serializer):
    """
    Serializer for creating order items.
    """
    product = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=True, min_value=1)
    
    def validate(self, data):
        """Validate product existence and availability."""
        product_id = data.get('product')
        quantity = data.get('quantity')
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError(f"Product with ID {product_id} not found or inactive")
        
        # Check stock
        if product.quantity < quantity:
            raise serializers.ValidationError(f"Insufficient stock for product: {product.name}")
        
        data['product_obj'] = product
        data['unit_price'] = product.price
        return data


class OrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating orders with items and delivery details.
    """
    customer_name = serializers.CharField(required=True)
    delivery_city = serializers.CharField(required=False, allow_blank=True)
    delivery_address = serializers.JSONField(required=False)
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_METHOD_CHOICES, default=Order.PAYMENT_METHOD_COD)
    items = OrderCreateItemSerializer(many=True, required=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate(self, data):
        """Validate order data."""
        user = self.context.get('request').user
        tenant = self.context.get('tenant')
        
        # Validate items
        items_data = data.get('items', [])
        if not items_data:
            raise serializers.ValidationError("At least one item is required")
        
        # Validate coupon if provided
        coupon_code = data.get('coupon_code')
        if coupon_code:
            try:
                coupon = Coupon.objects.get(
                    code=coupon_code,
                    tenant=tenant,
                    is_active=True,
                    valid_from__lte=timezone.now(),
                    valid_to__gte=timezone.now()
                )
                if coupon.used_count >= coupon.usage_limit:
                    raise serializers.ValidationError("Coupon usage limit exceeded")
                data['coupon'] = coupon
            except Coupon.DoesNotExist:
                raise serializers.ValidationError("Invalid or expired coupon code")
        
        # Calculate totals
        subtotal = Decimal('0')
        for item in items_data:
            subtotal += item['unit_price'] * item['quantity']
        
        # Apply member discount (if user has membership)
        # Note: You'll need to implement this based on your actual user model
        member_discount = Decimal('0')
        # Example: if user has membership tier
        # if hasattr(user, 'membership') and user.membership:
        #     member_discount = (subtotal * user.membership.discount_percentage) / Decimal('100')
        
        # Apply coupon discount
        coupon_discount = Decimal('0')
        if 'coupon' in data:
            coupon = data['coupon']
            if coupon.discount_type == 'percentage':
                coupon_discount = (subtotal * coupon.discount_value) / Decimal('100')
            else:
                coupon_discount = coupon.discount_value
            
            # Cap coupon discount at subtotal
            if coupon_discount > subtotal:
                coupon_discount = subtotal
        
        # Calculate total discount
        total_discount = member_discount + coupon_discount
        
        # Apply max discount
        if total_discount > subtotal:
            total_discount = subtotal
        
        # Calculate final total
        delivery_charge = Decimal('0')
        tax = subtotal * Decimal('0.13')  # 13% tax
        final_total = subtotal - total_discount + delivery_charge + tax
        
        # Update data with calculated values
        data['original_amount'] = subtotal
        data['discount_amount'] = total_discount
        data['total_price'] = final_total
        
        return data


class PrescriptionUploadSerializer(serializers.Serializer):
    """
    Serializer for uploading prescription images.
    """
    image = serializers.ImageField(required=True)
    
    def validate_image(self, value):
        """
        Validate uploaded image.
        """
        # Check file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image size should not exceed 5MB")
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"File type not supported. Allowed types: {', '.join(allowed_types)}"
            )
        
        return value


class PrescriptionReviewSerializer(serializers.Serializer):
    """
    Serializer for reviewing prescriptions.
    """
    status = serializers.ChoiceField(choices=['approved', 'rejected'], required=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate_status(self, value):
        """
        Validate status value.
        """
        if value not in ['approved', 'rejected']:
            raise serializers.ValidationError("Status must be 'approved' or 'rejected'")
        return value


class PrescriptionDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for prescription data.
    """
    order_number = serializers.CharField(source='order.id', read_only=True)
    user_email = serializers.EmailField(source='order.user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = OrderPrescription
        fields = [
            'id',
            'order',
            'order_number',
            'user_email',
            'user_name',
            'image',
            'status',
            'status_display',
            'uploaded_at',
            'reviewed_by',
            'reviewed_by_email',
            'reviewed_at',
            'notes',
        ]
        read_only_fields = ['uploaded_at', 'reviewed_at']
    
    def get_user_name(self, obj):
        """Get user's full name."""
        if obj.order.user:
            if hasattr(obj.order.user, 'get_full_name'):
                return obj.order.user.get_full_name() or obj.order.user.email
            return obj.order.user.email
        return None
    
    def to_representation(self, instance):
        """Add prescription image URL."""
        data = super().to_representation(instance)
        if instance.image:
            data['image_url'] = instance.image.url
        return data


class OrderPrescriptionStatusSerializer(serializers.Serializer):
    """
    Serializer for returning prescription status information.
    """
    requires_prescription = serializers.BooleanField()
    prescription_status = serializers.CharField(allow_null=True)
    prescription_uploaded = serializers.BooleanField()
    can_upload = serializers.BooleanField()
    can_review = serializers.BooleanField()
    message = serializers.CharField(allow_null=True)


# Helper function
def get_order_prescription_status(order):
    """
    Helper function to get prescription status for an order.
    """
    requires_prescription = order.items.filter(product__requires_prescription=True).exists()
    
    if not requires_prescription:
        return {
            'requires_prescription': False,
            'prescription_status': None,
            'prescription_uploaded': False,
            'can_upload': False,
            'can_review': False,
            'message': 'No prescription required for this order'
        }
    
    if hasattr(order, 'prescription'):
        prescription = order.prescription
        return {
            'requires_prescription': True,
            'prescription_status': prescription.status,
            'prescription_uploaded': True,
            'can_upload': False,
            'can_review': prescription.status == 'pending',
            'message': f'Prescription is {prescription.status}'
        }
    
    return {
        'requires_prescription': True,
        'prescription_status': None,
        'prescription_uploaded': False,
        'can_upload': True,
        'can_review': False,
        'message': 'Prescription not yet uploaded'
    }