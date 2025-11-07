from django.utils import timezone
from .models import Booking, FinanceTransaction
from .utils import send_notification

def auto_expire_bookings():
    """Automatically expire bookings that have passed their expiry date and create refunds."""
    today = timezone.now().date()
    expired = Booking.objects.filter(status='prebooked', expiry_date__lt=today)

    for booking in expired:
        # Calculate refund amount (only verified payments)
        total_paid = booking.get_total_paid()
        
        # Create refund transaction if there are verified payments
        if total_paid > 0:
            FinanceTransaction.objects.create(
                transaction_type='refund',
                amount=total_paid,
                booking=booking,
                student=booking.student,
                description=f"Automatic refund for expired booking - {booking.room}",
                status='completed',
                date_completed=timezone.now()
            )
        
        booking.status = 'expired'
        booking.save()
        
        # Update room vacancy
        if booking.room:
            booking.room.update_vacancy()
        
        refund_message = f"\n\nRefund Information:\nAny verified payments (Ksh {total_paid:,.2f}) have been automatically processed and sent to the finance office for refund." if total_paid > 0 else ""
        message = (
            f"Hello {booking.student.user.get_full_name()},\n\n"
            f"Your pre-booking for room {booking.room} has expired.\n{refund_message}\n\n"
            f"You can book a new room from your dashboard.\n\n"
            f"ANU Hostel Management System"
        )
        send_notification(booking.student, "Hostel Booking Expired", message)
