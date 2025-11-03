from django.utils import timezone
from datetime import timedelta
from .models import Booking
from .utils import send_notification

def check_payment_expiry():
    """Automatically flag unpaid bookings and notify students."""
    today = timezone.now().date()
    expired_bookings = Booking.objects.filter(status="prebooked", expiry_date__lt=today)

    for booking in expired_bookings:
        booking.status = "expired"
        booking.save()

        subject = "Payment Period Expired"
        message = (
            f"Dear {booking.student.user.get_full_name()},\n\n"
            f"Your pre-booking for {booking.room} has expired because payment was not completed in time.\n"
            f"The room may now be released to another student.\n\n"
            f"Please contact the hostel office for clarification.\n\n"
            f"– ANU Hostel Management System"
        )
        send_notification(booking.student, subject, message)
