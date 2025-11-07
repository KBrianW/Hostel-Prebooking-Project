from django.utils import timezone
from datetime import timedelta
from .models import Booking, FinanceTransaction
from .utils import send_notification

def check_payment_expiry():
    """Automatically flag unpaid bookings and notify students. Create refunds for verified payments."""
    today = timezone.now().date()
    expired_bookings = Booking.objects.filter(status="prebooked", expiry_date__lt=today)

    for booking in expired_bookings:
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
        
        booking.status = "expired"
        booking.save()
        
        # Update room vacancy
        if booking.room:
            booking.room.update_vacancy()

        subject = "Payment Period Expired"
        refund_message = f"\n\nRefund Information:\nAny verified payments (Ksh {total_paid:,.2f}) have been automatically processed and sent to the finance office for refund." if total_paid > 0 else ""
        message = (
            f"Dear {booking.student.user.get_full_name()},\n\n"
            f"Your pre-booking for {booking.room} has expired because payment was not completed in time.\n"
            f"The room may now be released to another student.\n{refund_message}\n\n"
            f"You can book a new room from your dashboard.\n\n"
            f"Please contact the hostel office for clarification.\n\n"
            f"– ANU Hostel Management System"
        )
        send_notification(booking.student, subject, message)
