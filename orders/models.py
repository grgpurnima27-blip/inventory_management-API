# orders/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

from products.models import Product
from inventory.models import Warehouse
from tenants.models import Tenant


class Order(models.Model):
    """
    Order model representing customer purchases.
    """
    # Status choices
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_SHIPPED = 'shipped'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    
    # Payment method choices
    PAYMENT_METHOD_ESEWA = 'esewa'
    PAYMENT_METHOD_KHALTI = 'khalti'
    PAYMENT_METHOD_COD = 'cod'
    
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_ESEWA, 'eSewa'),
        (PAYMENT_METHOD_KHALTI, 'Khalti'),
        (PAYMENT_METHOD_COD, 'Cash on Delivery'),
    ]
    
    # Payment status choices
    PAYMENT_STATUS_PENDING = 'pending'
    PAYMENT_STATUS_PAID = 'paid'
    PAYMENT_STATUS_FAILED = 'failed'
    PAYMENT_STATUS_REFUNDED = 'refunded'
    
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PENDING, 'Pending'),
        (PAYMENT_STATUS_PAID, 'Paid'),
        (PAYMENT_STATUS_FAILED, 'Failed'),
        (PAYMENT_STATUS_REFUNDED, 'Refunded'),
    ]
    
    # Fields
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    customer_name = models.CharField(max_length=255)
    delivery_city = models.CharField(max_length=100)
    delivery_address = models.JSONField(null=True, blank=True)
    
    # Order details
    original_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    delivery_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    
    # Payment related
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default=PAYMENT_METHOD_COD
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_STATUS_PENDING
    )
    payment_transaction_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    
    # Status and timestamps
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['payment_transaction_id']),
        ]
    
    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"
    
    @property
    def is_paid(self):
        return self.payment_status == self.PAYMENT_STATUS_PAID
    
    @property
    def can_cancel(self):
        return self.status in [self.STATUS_PENDING, self.STATUS_PROCESSING]
    
    @property
    def total_items(self):
        return self.items.count()


class OrderItem(models.Model):
    """
    Individual items within an order.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='order_items',
        null=True,
        blank=True
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['order', 'product']),
        ]
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    @property
    def total_price(self):
        return self.unit_price * self.quantity


# REMOVED: Payment model - using payment app instead


class Delivery(models.Model):
    """
    Delivery tracking for orders.
    """
    DELIVERY_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('returned', 'Returned'),
    ]
    
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='delivery'
    )
    status = models.CharField(
        max_length=20,
        choices=DELIVERY_STATUS_CHOICES,
        default='pending'
    )
    tracking_number = models.CharField(max_length=255, null=True, blank=True)
    tracking_url = models.URLField(null=True, blank=True)
    delivery_partner = models.CharField(max_length=100, null=True, blank=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivery_notes = models.TextField(blank=True)
    
    # Delivery address details
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Nepal')
    phone_number = models.CharField(max_length=20, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tracking_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Delivery {self.id} - Order {self.order.id}"
    
    def mark_shipped(self, tracking_number=None, delivery_partner=None):
        """Mark delivery as shipped."""
        self.status = 'shipped'
        if tracking_number:
            self.tracking_number = tracking_number
        if delivery_partner:
            self.delivery_partner = delivery_partner
        self.estimated_delivery = timezone.now() + timezone.timedelta(days=7)
        self.save()
        
        # Update order status
        self.order.status = Order.STATUS_SHIPPED
        self.order.shipped_at = timezone.now()
        self.order.save()
    
    def mark_delivered(self):
        """Mark delivery as delivered."""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save()
        
        # Update order status
        self.order.status = Order.STATUS_COMPLETED
        self.order.completed_at = timezone.now()
        self.order.save()


class OrderPrescription(models.Model):
    """
    Prescription model for orders that require prescription.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
    
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='prescription'
    )
    image = models.ImageField(upload_to='prescriptions/%Y/%m/')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_prescriptions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Review notes or rejection reason")
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['order', 'status']),
        ]
    
    def __str__(self):
        return f"Prescription for Order #{self.order.id} - {self.status}"
    
    def approve(self, reviewer, notes=None):
        """Approve the prescription."""
        self.status = self.Status.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        if notes:
            self.notes = notes
        self.save()
    
    def reject(self, reviewer, notes=None):
        """Reject the prescription."""
        self.status = self.Status.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        if notes:
            self.notes = notes
        self.save()
    
    @property
    def is_pending(self):
        return self.status == self.Status.PENDING
    
    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED
    
    @property
    def is_rejected(self):
        return self.status == self.Status.REJECTED


# orders/models.py - Update the Invoice model

class Invoice(models.Model):
    """
    Invoice model for order billing.
    """
    INVOICE_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='invoice'
    )
    invoice_number = models.CharField(max_length=50, unique=True, null=True, blank=True)  # Allow null
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Add default
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Add default
    status = models.CharField(
        max_length=20,
        choices=INVOICE_STATUS_CHOICES,
        default='draft'
    )
    pdf_file = models.FileField(upload_to='invoices/%Y/%m/', null=True, blank=True)
    
    # Billing details
    billing_address = models.JSONField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.order.id}"
    
    def issue(self):
        """Issue the invoice."""
        self.status = 'issued'
        self.issued_at = timezone.now()
        self.save()
    
    def mark_paid(self):
        """Mark invoice as paid."""
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save()