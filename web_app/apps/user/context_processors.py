from pages.models import UserNotification


def notification_summary(request):
    if not request.user.is_authenticated:
        return {
            "recent_notifications": [],
            "unread_notification_count": 0,
        }
    notifications = list(
        UserNotification.objects.filter(user_id=request.user.id)[:10]
    )
    return {
        "recent_notifications": notifications,
        "unread_notification_count": UserNotification.objects.filter(
            user_id=request.user.id, is_read=False
        ).count(),
    }
