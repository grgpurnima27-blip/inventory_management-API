# cart/urls.py

from django.urls import path

from .views import (
    CartView,
    AddToCartView,
    UpdateCartItemView,
    DeleteCartItemView,
    ClearCartView,
    ApplyCouponView,
    RemoveCouponView,
    CartSummaryView,
    SaveForLaterView,
    SavedItemsView,
    MoveToCartView,
    DeleteSavedItemView,
    CartCheckoutView,
)

urlpatterns = [
    # Cart
    path("", CartView.as_view(), name="cart"),
    path("add/", AddToCartView.as_view(), name="cart-add"),
    path("summary/", CartSummaryView.as_view(), name="cart-summary"),
    path("checkout/", CartCheckoutView.as_view(), name="cart-checkout"),
    path("clear/", ClearCartView.as_view(), name="cart-clear"),

    # Cart Items
    path("item/<int:pk>/", UpdateCartItemView.as_view(), name="cart-item-update"),
    path("item/<int:pk>/delete/", DeleteCartItemView.as_view(), name="cart-item-delete"),

    # Coupons
    path("apply-coupon/", ApplyCouponView.as_view(), name="cart-apply-coupon"),
    path("remove-coupon/", RemoveCouponView.as_view(), name="cart-remove-coupon"),

    # Save For Later
    path("save-for-later/", SaveForLaterView.as_view(), name="save-for-later"),
    path("saved-items/", SavedItemsView.as_view(), name="saved-items"),
    path("move-to-cart/", MoveToCartView.as_view(), name="move-to-cart"),
    path(
        "saved-items/<int:pk>/delete/",
        DeleteSavedItemView.as_view(),
        name="delete-saved-item",
    ),
]