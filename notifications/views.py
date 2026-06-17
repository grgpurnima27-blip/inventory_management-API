from django.shortcuts import render

# Create your views here.
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """List all notifications for the logged-in user"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    # Added this   to fix Swagger warning
    queryset = Notification.objects.none()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)


class NotificationMarkReadView(APIView):
    """Mark a single notification as read"""
    permission_classes = [IsAuthenticated]
    # Added here   serializer_class to fix warning
    serializer_class = NotificationSerializer

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
            notification.is_read = True
            notification.save()
            return Response({'detail': 'Notification marked as read.'})
        except Notification.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)


class NotificationMarkAllReadView(APIView):
    """Mark all notifications as read"""
    permission_classes = [IsAuthenticated]
    # Added here   serializer_class to fix warning
    serializer_class = NotificationSerializer

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        qs = Notification.objects.filter(user=request.user, is_read=False)
        if tenant:
            qs = qs.filter(tenant=tenant)
        qs.update(is_read=True)
        return Response({'detail': 'All notifications marked as read.'})


class NotificationDeleteView(generics.DestroyAPIView):
    """Delete a single notification"""
    permission_classes = [IsAuthenticated]
    # Added here serializer_class to fix warning
    serializer_class = NotificationSerializer
    # Added here queryset for Swagger
    queryset = Notification.objects.none()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)


class NotificationUnreadCountView(APIView):
    """Get count of unread notifications"""
    permission_classes = [IsAuthenticated]
    # Added here serializer_class to fix warning
    serializer_class = NotificationSerializer

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})