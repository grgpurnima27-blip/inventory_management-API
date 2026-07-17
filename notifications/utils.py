# from .models import Notification


# def send_notification(user, notification_type, order_id):
#     """Helper function to create notifications for order status changes"""

#     messages = {
#         'order_placed': {
#             'title':   f'Order #{order_id} Placed Successfully',
#             'message': f'Your order #{order_id} has been placed and is awaiting processing.',
#         },
#         'order_processing': {
#             'title':   f'Order #{order_id} is Being Processed',
#             'message': f'Great news! Your order #{order_id} is currently being processed.',
#         },
#         'order_shipped': {
#             'title':   f'Order #{order_id} Has Been Shipped',
#             'message': f'Your order #{order_id} is on its way! You will receive it soon.',
#         },
#         'order_completed': {
#             'title':   f'Order #{order_id} Delivered Successfully',
#             'message': f'Your order #{order_id} has been delivered. Thank you for shopping with us!',
#         },
#         'order_cancelled': {
#             'title':   f'Order #{order_id} Cancelled',
#             'message': f'Your order #{order_id} has been cancelled. Any deducted stock has been restored.',
#         },
#     }

#     data = messages.get(notification_type)
#     if data:
#         Notification.objects.create(
#             user    = user,
#             type    = notification_type,
#             title   = data['title'],
#             message = data['message'],
#         )

from .models import Notification


def send_notification(order, notification_type):
    """Create a notification for an order status change."""

    messages = {
        "order_placed": {
            "title": f"Order #{order.id} Placed Successfully",
            "message": (
                f"Your order #{order.id} has been placed "
                "and is awaiting processing."
            ),
        },
        "order_processing": {
            "title": f"Order #{order.id} is Being Processed",
            "message": (
                f"Great news! Your order #{order.id} "
                "is currently being processed."
            ),
        },
        "order_shipped": {
            "title": f"Order #{order.id} Has Been Shipped",
            "message": (
                f"Your order #{order.id} is on its way. "
                "You will receive it soon."
            ),
        },
        "order_completed": {
            "title": f"Order #{order.id} Delivered Successfully",
            "message": (
                f"Your order #{order.id} has been delivered. "
                "Thank you for shopping with us!"
            ),
        },
        "order_cancelled": {
            "title": f"Order #{order.id} Cancelled",
            "message": f"Your order #{order.id} has been cancelled.",
        },
    }

    data = messages.get(notification_type)

    if not data:
        return None

    return Notification.objects.create(
        tenant=order.tenant,
        user=order.user,
        type=notification_type,
        title=data["title"],
        message=data["message"],
    )