from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string


def send_verification_email(user, token: str):
    """Send email verification link to newly registered user."""
    verification_url = (
        f"{settings.FRONTEND_URL}/api/auth/verify-email/{token}/"
    )

    subject = "Verify your Inventory Management API account"

    ### Just filename — Django looks in email_templates/ folder automatically
    message = render_to_string('verification.html', {
        'username': user.username,
        'verification_url': verification_url,
    })

    send_mail(
        subject=subject,
        message=f"Click this link to verify your email: {verification_url}",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        html_message=message,
        fail_silently=False,
    )


def send_password_reset_email(user, token: str):
    """Send password reset link to user."""
    reset_url = (
        f"{settings.FRONTEND_URL}/api/auth/reset-password/{token}/"
    )

    subject = "Reset your Inventory Management API password"

    ###Just filename — Django looks in email_templates/ folder automatically
    message = render_to_string('reset_password.html', {
        'username': user.username,
        'reset_url': reset_url,
    })

    send_mail(
        subject=subject,
        message=f"Click this link to reset your password: {reset_url}",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        html_message=message,
        fail_silently=False,
    )