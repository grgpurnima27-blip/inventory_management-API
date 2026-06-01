from .models import Notification


def send_notification(user, notification_type, order_id):
    """Helper function to create notifications for order status changes"""

    messages = {
        'order_placed': {
            'title':   f'Order #{order_id} Placed Successfully',
            'message': f'Your order #{order_id} has been placed and is awaiting processing.',
        },
        'order_processing': {
            'title':   f'Order #{order_id} is Being Processed',
            'message': f'Great news! Your order #{order_id} is currently being processed.',
        },
        'order_shipped': {
            'title':   f'Order #{order_id} Has Been Shipped',
            'message': f'Your order #{order_id} is on its way! You will receive it soon.',
        },
        'order_completed': {
            'title':   f'Order #{order_id} Delivered Successfully',
            'message': f'Your order #{order_id} has been delivered. Thank you for shopping with us!',
        },
        'order_cancelled': {
            'title':   f'Order #{order_id} Cancelled',
            'message': f'Your order #{order_id} has been cancelled. Any deducted stock has been restored.',
        },
    }

    data = messages.get(notification_type)
    if data:
        Notification.objects.create(
            user    = user,
            type    = notification_type,
            title   = data['title'],
            message = data['message'],
        )