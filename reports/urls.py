from django.urls import path

from .views import InventorySummaryView

urlpatterns = [

    path(
        'inventory-summary/',
        InventorySummaryView.as_view(),
        name='inventory-summary'
    ),
]