from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class KhaltiWebhookView(APIView):

    authentication_classes = []
    permission_classes = []

    def post(self, request):

        # We will implement verification later.

        return Response(
            {
                "message": "Khalti webhook received."
            },
            status=status.HTTP_200_OK,
        )


class EsewaWebhookView(APIView):

    authentication_classes = []
    permission_classes = []

    def post(self, request):

        return Response(
            {
                "message": "eSewa webhook received."
            },
            status=status.HTTP_200_OK,
        )