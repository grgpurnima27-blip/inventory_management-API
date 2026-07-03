from django.urls import path
from .views import (
    InventorySummaryAPIView,
    TopProductsReportAPIView,
    RevenueByCityAPIView,
    TopCustomersReportAPIView,
    SalesChartReportAPIView,
    CouponUsageReportAPIView,
	VendorDashboardReportAPIView,
)

urlpatterns = [
    path(
        'inventory-summary/',
        InventorySummaryAPIView.as_view(),
        name='inventory-summary'
    ),
    path(
        'top-products/',
        TopProductsReportAPIView.as_view(),
        name='top-products'
    ),
    path(
        'revenue-by-city/',
        RevenueByCityAPIView.as_view(),
        name='revenue-by-city'
    ),
    path(
        'top-customers/',
        TopCustomersReportAPIView.as_view(),
        name='top-customers'
    ),
    path(
        'sales-chart/',
        SalesChartReportAPIView.as_view(),
        name='sales-chart'
    ),
    path(
        'coupon-usage/',
        CouponUsageReportAPIView.as_view(),
        name='coupon-usage'
    ),
	path(
    'vendor-dashboard/',
    VendorDashboardReportAPIView.as_view(),
    name='vendor-dashboard'
),

]