from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from products.models import Product
from coupons.models import Coupon


class Cart(models.Model):
    """
    One active cart per user.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )

    applied_coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.username}'s Cart"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        total = Decimal("0.00")

        for item in self.items.select_related("product"):
            total += item.subtotal

        return total

    @property
    def discount_amount(self):

        if not self.applied_coupon:
            return Decimal("0.00")

        coupon = self.applied_coupon

        if self.subtotal < coupon.minimum_order_amount:
            return Decimal("0.00")

        if coupon.discount_type == Coupon.TYPE_PERCENTAGE:
            discount = (
                self.subtotal * coupon.discount_value
            ) / Decimal("100")
        else:
            discount = coupon.discount_value

        if discount > self.subtotal:
            discount = self.subtotal

        return discount.quantize(Decimal("0.01"))

    @property
    def total(self):
        return (self.subtotal - self.discount_amount).quantize(
            Decimal("0.01")
        )


class CartItem(models.Model):
    """
    Product inside cart.
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )

    quantity = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "product")
        ordering = ["created_at"]

    def clean(self):

        if self.quantity <= 0:
            raise ValidationError(
                {
                    "quantity": "Quantity must be greater than zero."
                }
            )

        if self.product.quantity < self.quantity:
            raise ValidationError(
                {
                    "quantity": "Requested quantity exceeds available stock."
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    @property
    def vendor(self):
        return self.product.tenant

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class SavedItem(models.Model):
    """
    Save products for later.
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="saved_items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="saved_items",
    )

    quantity = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "product")
        ordering = ["-created_at"]

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product.name} (Saved for Later)"