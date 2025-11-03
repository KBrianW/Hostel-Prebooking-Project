from .models import Notification

def notification_context(request):
    """Inject notification data into templates."""
    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        notifications = Notification.objects.filter(student=student).order_by('-date_sent')
        unread_count = notifications.filter(is_read=False).count()
        return {
            'user_notifications': notifications,
            'unread_notifications_count': unread_count
        }
    return {}
