import logging

from django.conf import settings
from django.core.mail import send_mail
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ContactMessageSerializer


logger = logging.getLogger(__name__)


class ContactMessageAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ContactMessageSerializer,
        responses={
            201: ContactMessageSerializer,
            400: dict,
        },
        summary="Send contact message",
        description=(
            "Saves a contact message, sends it to the developer email, "
            "and sends a confirmation email to the customer."
        ),
        tags=["Contact"],
    )
    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contact_message = serializer.save()

        full_name = (
            f"{contact_message.first_name} "
            f"{contact_message.last_name}"
        ).strip()

        support_email_sent = False
        customer_email_sent = False

        try:
            send_mail(
                subject=f"New contact message: {contact_message.subject}",
                message=(
                    "A new contact form message was submitted.\n\n"
                    f"Name: {full_name}\n"
                    f"Email: {contact_message.email}\n"
                    f"Subject: {contact_message.subject}\n\n"
                    f"Message:\n{contact_message.message}\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.SUPPORT_EMAIL],
                fail_silently=False,
            )
            support_email_sent = True

        except Exception as exc:
            logger.exception(
                "Could not send contact message to support: %s",
                exc,
            )

        try:
            send_mail(
                subject="We received your message",
                message=(
                    f"Hello {contact_message.first_name},\n\n"
                    "Thank you for contacting us.\n\n"
                    "We have received your message and will respond "
                    "as soon as possible.\n\n"
                    f"Subject: {contact_message.subject}\n\n"
                    "Regards,\n"
                    "Support Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[contact_message.email],
                fail_silently=False,
            )
            customer_email_sent = True

        except Exception as exc:
            logger.exception(
                "Could not send contact confirmation email: %s",
                exc,
            )

        return Response(
            {
                "message": "Your message was submitted successfully.",
                "support_email_sent": support_email_sent,
                "confirmation_email_sent": customer_email_sent,
                "data": ContactMessageSerializer(contact_message).data,
            },
            status=status.HTTP_201_CREATED,
        )