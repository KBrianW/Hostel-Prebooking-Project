from .models import Notification, Booking

def notification_context(request):
    """Inject notification data into templates."""
    if request.user.is_authenticated:
        # For students
        if hasattr(request.user, 'student'):
            student = request.user.student
            notifications = Notification.objects.filter(student=student).order_by('-date_sent')
            unread_count = notifications.filter(is_read=False).count()
            
            # Check if student has fully paid booking (for showing Roommates link)
            booking = Booking.objects.filter(student=student).order_by('-date_booked').first()
            can_view_roommates = booking.is_fully_paid() if booking else False
            
            return {
                'user_notifications': notifications,
                'unread_notifications_count': unread_count,
                'can_view_roommates': can_view_roommates,
            }
        # For staff/admins (no notifications for now, but return empty to avoid errors)
        return {
            'user_notifications': [],
            'unread_notifications_count': 0,
            'can_view_roommates': False,
        }
    # For unauthenticated users, return empty dict
    return {
        'user_notifications': [],
        'unread_notifications_count': 0,
        'can_view_roommates': False,
    }
