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
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=[
        ('Regular', 'Regular'),
        ('Ensuite', 'Ensuite'),
    ])
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

    def __str__(self):
        return f"{self.hostel.name} - Room {self.room_number}"


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
        """Return all other students sharing the same room."""
        if not self.room:
            return []
        return Booking.objects.filter(room=self.room, status='paid').exclude(student=self.student)

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

        from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender='core.Payment')
def verify_payment(sender, instance, **kwargs):
    """Automatically mark booking as paid when finance verifies payment."""
    if instance.verified:
        booking = instance.booking
        booking.status = 'paid'
        booking.save()

        # Notify the student
        student = booking.student
        subject = "Hostel Payment Verified"
        message = (
            f"Hello {student.user.get_full_name()},\n\n"
            f"Your payment of Ksh {instance.amount} has been verified successfully.\n"
            f"You are now fully booked for room {booking.room}.\n\n"
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

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender='core.Booking')
def update_room_vacancy(sender, instance, **kwargs):
    """Automatically update room vacancy after booking or payment."""
    room = instance.room
    if not room:
        return
    
    total_paid = Booking.objects.filter(room=room, status='paid').count()
    if total_paid >= room.capacity:
        room.is_vacant = False
    else:
        room.is_vacant = True
    room.save()
