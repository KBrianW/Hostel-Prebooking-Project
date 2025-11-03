from django.utils import timezone
from .models import Booking
from .utils import send_notification

def auto_expire_bookings():
    """Automatically expire bookings that have passed their expiry date."""
    today = timezone.now().date()
    expired = Booking.objects.filter(status='prebooked', expiry_date__lt=today)

    for booking in expired:
        booking.status = 'expired'
        booking.save()
        message = (
            f"Hello {booking.student.user.get_full_name()},\n\n"
            f"Your pre-booking for room {booking.room} has expired.\n"
            f"Please contact the hostel office for further assistance.\n\n"
            f"ANU Hostel Management System"
        )
        send_notification(booking.student, "Hostel Booking Expired", message)
