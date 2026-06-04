from django.urls import path

from .views import (
    RegisterView,
    LoginView,
    AdminLoginView,
    MeView,
    ChangePasswordView,
    LogoutView,
    ForgotPasswordView,
    ResetPasswordView,
)

from .jwt_views import CustomTokenRefreshView


urlpatterns = [

    # Authentication
    path('register/',RegisterView.as_view(),             name='register'),
    path('login/',LoginView.as_view(),                name='login'),
    path('admin/login/',AdminLoginView.as_view(),           name='admin-login'),
    path('me/',MeView.as_view(),                   name='me'),
    path('token/refresh/',                  CustomTokenRefreshView.as_view(),   name='token-refresh'),
    
    # Password Management
    path('change-password/',                ChangePasswordView.as_view(),       name='change-password'),
    path('logout/',LogoutView.as_view(),               name='logout'),

    # Password Reset
    path('forgot-password/',                ForgotPasswordView.as_view(),       name='forgot-password'),
    path('reset-password/<str:token>/',     ResetPasswordView.as_view(),        name='reset-password'),
]