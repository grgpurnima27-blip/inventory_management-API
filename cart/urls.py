from django.urls import path

from .views import (
    CartView,
    AddToCartView,
    UpdateCartItemView,
    RemoveCartItemView,
	CartCheckoutView,
)

urlpatterns = [

    path(
        '',
        CartView.as_view(),
        name='cart'
    ),

    path(
        'add/',
        AddToCartView.as_view(),
        name='add-cart'
    ),

    path(
        'item/<int:item_id>/',
        UpdateCartItemView.as_view(),
        name='update-cart-item'
    ),

    path(
        'item/<int:item_id>/delete/',
        RemoveCartItemView.as_view(),
        name='remove-cart-item'
    ),
	path(
    "checkout/",
    CartCheckoutView.as_view(),
    name="cart-checkout"
),
]








