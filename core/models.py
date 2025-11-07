from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .utils import send_notification


# -----------------------------
# STUDENT MODEL
# -----------------------------
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    reg_no = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    course = models.CharField(max_length=100, blank=True, null=True)
    year_of_study = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.reg_no})"


# -----------------------------
# HOSTEL MODEL
# -----------------------------
class Hostel(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]
    ROOM_TYPE_CHOICES = [
        ('Type 1', 'Type 1'),
        ('Ensuite', 'Ensuite'),
        ('Regular', 'Regular'),
    ]
    
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Male')
    type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES, default='Regular')
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


# -----------------------------
# ROOM MODEL
# -----------------------------
class Room(models.Model):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=10)
    capacity = models.PositiveIntegerField(default=2)
    is_vacant = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=24000)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.hostel.name} - Room {self.room_number}"
    
    def get_occupied_count(self):
        """Get the number of active students in this room (prebooked or fully paid)."""
        # Use string reference to avoid circular import
        from django.apps import apps
        Booking = apps.get_model('core', 'Booking')
        # Count both prebooked and paid bookings (exclude expired)
        return Booking.objects.filter(room=self, status__in=['prebooked', 'paid']).count()
    
    def update_vacancy(self):
        """Update vacancy based on active bookings. Occupied only if capacity is reached (e.g., 2/2 students)."""
        occupied_count = self.get_occupied_count()
        # Room is occupied if it has reached capacity (e.g., 2/2), vacant if 0/2 or 1/2
        if occupied_count >= self.capacity:
            self.is_vacant = False
        else:
            self.is_vacant = True
        self.save()


# -----------------------------
# BOOKING MODEL (add this method inside Booking)
# -----------------------------
class Booking(models.Model):
    STATUS_CHOICES = [
        ('prebooked', 'Pre-booked'),
        ('paid', 'Fully Paid'),
        ('expired', 'Expired'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='bookings')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    date_booked = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='prebooked')
    expiry_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.reg_no} - {self.room}"

    def get_roommates(self):
        """Return all other students sharing the same room (only if booking is fully paid)."""
        if not self.room or self.status != 'paid':
            return []
        return Booking.objects.filter(room=self.room, status='paid').exclude(student=self.student)
    
    def get_total_paid(self):
        """Calculate total amount paid for this booking (verified payments only)."""
        return sum(p.amount for p in self.payments.filter(verified=True))
    
    def get_total_paid_all(self):
        """Calculate total amount paid including unverified payments (for student display)."""
        return sum(p.amount for p in self.payments.all())
    
    def get_total_due(self):
        """Get the total amount due for this booking."""
        if self.room:
            return self.room.price
        return 0
    
    def is_fully_paid(self):
        """Check if booking is fully paid."""
        return self.get_total_paid() >= self.get_total_due() and self.status == 'paid'

# -----------------------------
# PAYMENT MODEL
# -----------------------------
class Payment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateTimeField(auto_now_add=True)
    payment_type = models.CharField(max_length=20, choices=[
        ('prepayment', 'Prepayment'),
        ('full', 'Full Payment'),
    ])
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.booking} - Ksh {self.amount}"

# -----------------------------
# FINANCE MODEL
# -----------------------------
class FinanceTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('payment', 'Payment Received'),
        ('refund', 'Refund Paid'),
        ('renewal', 'Renewal Payment'),  # Money used from finance account for renewals
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_created = models.DateTimeField(auto_now_add=True)
    date_completed = models.DateTimeField(null=True, blank=True)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_transactions')
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_transactions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    class Meta:
        ordering = ['-date_created']
    
    def __str__(self):
        return f"{self.transaction_type.upper()} - Ksh {self.amount} - {self.status}"
    

@receiver(post_save, sender='core.Payment')
def create_finance_transaction(sender, instance, created, **kwargs):
    """Create finance transaction when payment is created."""
    if created:
        from django.utils import timezone
        # Check if transaction already exists to avoid duplicates
        existing = FinanceTransaction.objects.filter(
            booking=instance.booking,
            transaction_type='payment',
            amount=instance.amount,
            date_created__date=timezone.now().date()
        ).first()
        
        if not existing:
            FinanceTransaction.objects.create(
                booking=instance.booking,
                transaction_type='payment',
                amount=instance.amount,
                student=instance.booking.student,
                description=f"Payment from {instance.booking.student.reg_no} - {instance.payment_type}",
                status='completed' if instance.verified else 'pending',
                date_completed=timezone.now() if instance.verified else None,
            )

@receiver(post_save, sender='core.Payment')
def verify_payment(sender, instance, **kwargs):
    """Update booking status when payment is verified. Only mark as paid if fully paid."""
    if instance.verified:
        booking = instance.booking
        total_paid = booking.get_total_paid()
        total_due = booking.get_total_due()
        
        # Update finance transaction status
        finance_trans = FinanceTransaction.objects.filter(
            booking=booking,
            transaction_type='payment',
            amount=instance.amount,
            status='pending'
        ).first()
        if finance_trans:
            finance_trans.status = 'completed'
            finance_trans.date_completed = instance.date_paid
            finance_trans.save()
        
        # Only mark as paid if fully paid
        if total_paid >= total_due:
            booking.status = 'paid'
            booking.save()
            
            # Update room vacancy
            if booking.room:
                booking.room.update_vacancy()
            
            # Notify the student
            student = booking.student
            subject = "Hostel Payment Fully Verified"
            message = (
                f"Hello {student.user.get_full_name()},\n\n"
                f"Your payment has been fully verified. Total paid: Ksh {total_paid}.\n"
                f"You are now fully booked for room {booking.room}.\n\n"
                f"Thank you,\nANU Hostel Management"
            )
            from .utils import send_notification
            send_notification(student, subject, message)
        else:
            # Partial payment verified
            student = booking.student
            subject = "Payment Verified (Partial)"
            message = (
                f"Hello {student.user.get_full_name()},\n\n"
                f"Your payment of Ksh {instance.amount} has been verified.\n"
                f"Total paid: Ksh {total_paid} / Ksh {total_due}.\n"
                f"Please complete the remaining payment.\n\n"
                f"Thank you,\nANU Hostel Management"
            )
            from .utils import send_notification
            send_notification(student, subject, message)

# -----------------------------
# NOTIFICATION MODEL
# -----------------------------
class Notification(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    date_sent = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    # Track delivery status
    email_status = models.CharField(max_length=20, default="Pending")  # Sent / Failed / No Email
    sms_status = models.CharField(max_length=20, default="Pending")    # Sent / Failed / No Phone

    def __str__(self):
        return f"Notification to {self.student.reg_no}"
# -----------------------------
# SIGNALS: Send Email After Pre-booking
# -----------------------------

@receiver(post_save, sender=Booking)
def send_booking_confirmation(sender, instance, created, **kwargs):
    if created and instance.status == 'prebooked':
        student = instance.student
        subject = "Hostel Pre-booking Confirmation"
        message = (
            f"Hello {student.user.get_full_name()},\n\n"
            f"Your room ({instance.room}) has been successfully pre-booked at ANU.\n"
            f"Please complete your remaining payment before the due date to confirm your spot.\n\n"
            f"Thank you,\nANU Hostel Management System"
        )
        send_notification(student, subject, message)

@receiver(post_save, sender='core.Booking')
def update_room_vacancy(sender, instance, **kwargs):
    """Automatically update room vacancy after booking status changes."""
    room = instance.room
    if not room:
        return
    
    # Update vacancy based on fully paid bookings only
    room.update_vacancy()
