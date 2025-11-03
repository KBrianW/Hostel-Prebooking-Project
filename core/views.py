from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Student, Room, Booking, Payment, Notification, Hostel
from django.db.models import Prefetch
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required




# -----------------------------
# STUDENT DASHBOARD (DYNAMIC)
# -----------------------------
@login_required
def student_dashboard(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student = None

    booking = Booking.objects.filter(student=student).order_by('-date_booked').first() if student else None
    notifications = Notification.objects.filter(student=student).order_by('-date_sent') if student else []

    # For dashboard: only latest 3 unread notifications
    latest_unread = Notification.objects.filter(student=student, is_read=False).order_by('-date_sent')[:3] if student else []

    roommates = booking.get_roommates() if booking and booking.status == 'paid' else []

    # Compute available rooms count by gender
    available_rooms_count = 0
    if student and student.gender:
        gender = (student.gender or 'male').lower()
        hostels = (
            Hostel.objects.filter(name__in=["Zanner", "Cashman", "Johnson"]) if gender == "male"
            else Hostel.objects.filter(name__icontains="Crawford")
        )
        available_rooms_count = Room.objects.filter(hostel__in=hostels, is_vacant=True).count()

    # Compute payment progress if booking exists
    progress = None
    remaining = None
    total_due = None
    if booking:
        # derive total_due by hostel/type
        if booking.room.hostel.name == 'Crawford Type 1':
            total_due = 35000
        elif booking.room.hostel.type == 'Ensuite':
            total_due = 28000
        else:
            total_due = 24000
        paid_amount = sum(p.amount for p in booking.payments.all()) if hasattr(booking, 'payments') else 0
        remaining = max(total_due - paid_amount, 0)
        progress = int((paid_amount / total_due) * 100) if total_due else 0

    context = {
        'student': student,
        'booking': booking,
        'notifications': notifications,
        'latest_unread_notifications': latest_unread,
        'roommates': roommates,
        'available_rooms_count': available_rooms_count,
        'payment_progress': progress,
        'payment_remaining': remaining,
        'payment_total': total_due,
    }
    return render(request, 'student_dashboard.html', context)


# -----------------------------
# ADMIN DASHBOARD
# -----------------------------
@login_required
def admin_dashboard(request):
    total_students = Student.objects.count()
    prebooked = Booking.objects.filter(status='prebooked').count()
    fully_paid = Booking.objects.filter(status='paid').count()
    vacant_rooms = Room.objects.filter(is_vacant=True).count()

    recent_bookings = Booking.objects.select_related('student', 'room').order_by('-date_booked')[:10]
    flagged_students = Booking.objects.filter(status='prebooked')

    context = {
        'total_students': total_students,
        'prebooked': prebooked,
        'fully_paid': fully_paid,
        'vacant_rooms': vacant_rooms,
        'recent_bookings': recent_bookings,
        'flagged_students': flagged_students,
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
def manage_bookings(request):
    if not request.user.is_staff:
        return redirect('student_dashboard')

    bookings = Booking.objects.select_related('student', 'room').order_by('-date_booked')

    if request.method == "POST":
        action = request.POST.get('action')
        booking_id = request.POST.get('booking_id')
        booking = Booking.objects.get(id=booking_id)

        # ✅ Mark payment verified
        if action == "verify":
            payment = booking.payments.last()
            if payment:
                payment.verified = True
                payment.save()
                booking.status = "paid"
                booking.save()

                # Send notification
                from .utils import send_notification
                subject = "Payment Verified"
                message = (
                    f"Hello {booking.student.user.get_full_name()},\n\n"
                    f"Your payment for {booking.room.hostel.name} - {booking.room.room_number} has been verified.\n"
                    "Your booking is now fully confirmed.\n\n"
                    "Thank you,\nANU Hostel Management System"
                )
                send_notification(booking.student, subject, message)

                messages.success(request, "Payment verified and booking confirmed.")

        # 🚪 Release room (cancel booking)
        elif action == "release":
            room = booking.room
            room.is_vacant = True
            room.save()
            booking.status = "expired"
            booking.save()

            messages.info(request, f"Room {room.room_number} released successfully.")

        return redirect('manage_bookings')

    return render(request, 'manage_bookings.html', {'bookings': bookings})

# -----------------------------
# LOGIN VIEW
# -----------------------------
def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.is_staff:
                return redirect('admin_dashboard')
            else:
                return redirect('student_dashboard')
        else:
            messages.error(request, "Invalid username or password")
    return render(request, 'login.html')


# -----------------------------
# LOGOUT VIEW
# -----------------------------
def logout_view(request):
    logout(request)
    return redirect('login')


# -----------------------------
# STUDENT PROFILE (Editable Fields: Username + Phone)
# -----------------------------
@login_required
def student_profile(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')
    student = Student.objects.get(user=request.user)
    user = request.user

    if request.method == "POST":
        new_username = request.POST.get('username')
        new_phone = request.POST.get('phone')

        # Update username if changed
        if new_username and new_username != user.username:
            user.username = new_username
            user.save()

        # Update phone number
        student.phone = new_phone
        student.save()

        messages.success(request, "Profile updated successfully!")

    return render(request, 'student_profile.html', {'student': student})

@login_required
def available_rooms(request):
    student = Student.objects.get(user=request.user)
    gender = (student.gender or "male").lower()

    # Block if already has active booking
    if Booking.objects.filter(student=student, status__in=['prebooked', 'paid']).exists():
        messages.warning(request, "You already have an active booking.")
        return redirect('student_dashboard')

    # Gender-based hostel filtering
    hostels = (
        Hostel.objects.filter(name__in=["Zanner", "Cashman", "Johnson"]) if gender == "male"
        else Hostel.objects.filter(name__icontains="Crawford")
    )

    rooms = Room.objects.filter(hostel__in=hostels, is_vacant=True)

    # Handle new pre-booking
    if request.method == "POST":
        room_id = request.POST.get("room_id")
        try:
            room = Room.objects.get(id=room_id, is_vacant=True)
        except Room.DoesNotExist:
            messages.error(request, "Room is no longer available.")
            return redirect('available_rooms')

        booking = Booking.objects.create(student=student, room=room, status="prebooked")
        Payment.objects.create(
            booking=booking,
            amount=2500,
            payment_type='prepayment',
            verified=True
        )

        room.is_vacant = False
        room.save()

        from .utils import send_notification
        subject = "Hostel Pre-booking Confirmation"
        message = (
            f"Dear {student.user.get_full_name()},\n\n"
            f"You have successfully pre-booked {room.hostel.name} - Room {room.room_number}.\n"
            "Please complete the remaining payment before reporting week.\n\n"
            "Thank you,\nANU Hostel Management System"
        )
        send_notification(student, subject, message)

        messages.success(request, f"You have successfully pre-booked {room.hostel.name} - {room.room_number}.")
        return redirect('student_dashboard')

    return render(request, 'available_rooms.html', {'rooms': rooms})

@login_required
def mark_notification_as_read(request, notification_id):
    """Mark a single notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, student__user=request.user)
    notification.is_read = True
    notification.save()
    return redirect(request.META.get('HTTP_REFERER', 'student_dashboard'))


@login_required
def mark_all_notifications_as_read(request):
    """Mark all notifications as read for the logged-in student."""
    Notification.objects.filter(student__user=request.user, is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'student_dashboard'))

# -----------------------------
# NOTIFICATIONS PAGE
# -----------------------------
@login_required
def notifications_page(request):
    # Student notifications page
    if request.user.is_staff:
        return redirect('admin_notifications_page')

    student = getattr(request.user, 'student', None)
    if not student:
        return redirect('student_dashboard')

    qs = Notification.objects.filter(student=student).order_by('-date_sent')
    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Mark visible page as read on load
    ids = [n.id for n in page_obj]
    Notification.objects.filter(id__in=ids, is_read=False).update(is_read=True)

    return render(request, 'notifications.html', {
        'page_obj': page_obj,
        'total_unread': qs.filter(is_read=False).count(),
    })

# -----------------------------
# ADMIN NOTIFICATIONS PAGE
# -----------------------------
@login_required
def admin_notifications_page(request):
    if not request.user.is_staff:
        return redirect('student_dashboard')

    # Build an operational feed for admins
    recent_bookings = (
        Booking.objects.select_related('student__user', 'room', 'room__hostel')
        .order_by('-date_booked')[:10]
    )
    awaiting_verification = (
        Booking.objects.select_related('student__user', 'room', 'room__hostel')
        .filter(status='prebooked')
        .order_by('-date_booked')[:10]
    )
    recent_payments = (
        Payment.objects.select_related('booking__student__user', 'booking__room__hostel')
        .order_by('-date')[:10]
        if hasattr(Payment, 'date') else []
    )

    # Simple pagination: flatten into sections rendered on one page (light-weight)
    context = {
        'recent_bookings': recent_bookings,
        'awaiting_verification': awaiting_verification,
        'recent_payments': recent_payments,
    }
    return render(request, 'admin_notifications.html', context)

@login_required
def fetch_notifications(request):
    """Return JSON with user's latest notifications.
    For students: returns unread count and 5 latest.
    For admins: returns count of items awaiting verification as the attention metric.
    """
    if request.user.is_staff:
        # Use count of prebooked bookings awaiting verification as admin attention count
        attention_count = Booking.objects.filter(status='prebooked').count()
        return JsonResponse({'unread_count': attention_count, 'notifications': []})

    student = getattr(request.user, 'student', None)
    if not student:
        return JsonResponse({'unread_count': 0, 'notifications': []})

    base_qs = Notification.objects.filter(student=student).order_by('-date_sent')
    unread_count = base_qs.filter(is_read=False).count()
    notifications = list(base_qs[:5])

    data = {
        'unread_count': unread_count,
        'notifications': [
            {
                'message': n.message,
                'date_sent': n.date_sent.strftime('%b %d, %Y %H:%M'),
                'is_read': n.is_read,
            } for n in notifications
        ]
    }
    return JsonResponse(data)

# -----------------------------
# REGISTRATION VIEW (simple)
# -----------------------------
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        reg_no = request.POST.get('reg_no')
        phone = request.POST.get('phone')
        gender = request.POST.get('gender')
        course = request.POST.get('course')
        year_of_study = request.POST.get('year_of_study')

        if not all([username, password, reg_no, phone, gender]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('register')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')

        user = User.objects.create_user(username=username, password=password,
                                        first_name=first_name or '', last_name=last_name or '')
        Student.objects.create(user=user, reg_no=reg_no, phone=phone, gender=gender,
                               course=course or '', year_of_study=year_of_study or '')
        messages.success(request, 'Account created. Please log in.')
        return redirect('login')

    return render(request, 'register.html')