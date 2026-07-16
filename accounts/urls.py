from django.urls import path

from .views import (
    RegisterView,
    LoginView,
    AdminLoginView,
    VendorRegisterView,
    VendorLoginView,
    EmployeeLoginView,
    MeView,
    ChangePasswordView,
    LogoutView,
    ForgotPasswordView,
    ResetPasswordView,
	VerifyEmailView,
)
from .google_auth import GoogleAuthView
from .jwt_views import CustomTokenRefreshView


urlpatterns = [

    # Authentication
    path('register/',                         RegisterView.as_view(),       name='register'),
    path('login/',                            LoginView.as_view(),          name='login'),
    path('admin/login/',                      AdminLoginView.as_view(),     name='admin-login'),
    path('vendor/register/',                  VendorRegisterView.as_view(), name='vendor-register'),
    path('vendor/login/',                     VendorLoginView.as_view(),    name='vendor-login'),
    path('employee/login/',                   EmployeeLoginView.as_view(),  name='employee-login'),
    path('me/',                               MeView.as_view(),           name='me'),
    path('token/refresh/',                  CustomTokenRefreshView.as_view(),   name='token-refresh'),
    
    # Password Management
    path('change-password/',                ChangePasswordView.as_view(),       name='change-password'),
    path('logout/',LogoutView.as_view(),               name='logout'),

    # Password Reset
    path('forgot-password/',                ForgotPasswordView.as_view(),       name='forgot-password'),
    path('reset-password/<str:token>/',     ResetPasswordView.as_view(),        name='reset-password'),
    # google oauth
    path('google/login', GoogleAuthView.as_view(), name='google-login'),
	path(
    'verify-email/<str:token>/',
    VerifyEmailView.as_view(),
    name='verify-email',
),
]