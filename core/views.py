from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Student, Room, Booking, Payment, Notification, Hostel, FinanceTransaction
from django.utils import timezone
from decimal import Decimal
from django.db.models import Prefetch, Sum, Q
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

    # Only show roommates if booking is fully paid
    roommates = booking.get_roommates() if booking and booking.is_fully_paid() else []

    # Compute available rooms count by gender
    available_rooms_count = 0
    if student and student.gender:
        gender = (student.gender or 'male').lower()
        hostels = (
            Hostel.objects.filter(gender="Male") if gender == "male"
            else Hostel.objects.filter(gender="Female")
        )
        available_rooms_count = Room.objects.filter(hostel__in=hostels, is_vacant=True).count()

    # Compute payment progress if booking exists
    progress = None
    remaining = None
    total_due = None
    if booking and booking.room:
        total_due = float(booking.get_total_due())
        # Use get_total_paid_all() to include unverified payments for student display
        paid_amount = float(booking.get_total_paid_all())  # Includes all payments
        remaining = max(total_due - paid_amount, 0)
        progress = int((paid_amount / total_due) * 100) if total_due > 0 else 0

    # Calculate Finance Account Balance for dashboard
    finance_total_refunded = Decimal('0.00')
    finance_total_used = Decimal('0.00')
    finance_available_balance = Decimal('0.00')
    
    if student:
        finance_total_refunded = FinanceTransaction.objects.filter(
            student=student,
            transaction_type='refund',
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        finance_total_used = FinanceTransaction.objects.filter(
            student=student,
            transaction_type='renewal',
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        finance_available_balance = finance_total_refunded - finance_total_used

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
        'finance_total_refunded': float(finance_total_refunded),
        'finance_total_used': float(finance_total_used),
        'finance_available_balance': float(finance_available_balance),
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
    expired = Booking.objects.filter(status='expired').count()
    vacant_rooms = Room.objects.filter(is_vacant=True).count()
    total_rooms = Room.objects.count()
    occupied_rooms = total_rooms - vacant_rooms
    
    # Payment statistics
    pending_payments = Payment.objects.filter(verified=False).count()
    total_pending_amount = Payment.objects.filter(verified=False).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    verified_payments_today = Payment.objects.filter(verified=True, date_paid__date=timezone.now().date()).count()
    
    # Recent bookings
    recent_bookings = Booking.objects.select_related('student', 'room', 'room__hostel').order_by('-date_booked')[:10]
    
    # Awaiting verification (prebooked with unverified payments)
    awaiting_verification = Booking.objects.filter(
        status='prebooked',
        payments__verified=False
    ).distinct().select_related('student', 'room', 'room__hostel').order_by('-date_booked')[:8]
    
    # Bookings expiring soon (within 3 days)
    from datetime import timedelta
    three_days_from_now = timezone.now().date() + timedelta(days=3)
    expiring_soon = Booking.objects.filter(
        status='prebooked',
        expiry_date__lte=three_days_from_now,
        expiry_date__gte=timezone.now().date()
    ).select_related('student', 'room', 'room__hostel').order_by('expiry_date')[:5]

    # Get pending payment details for awaiting verification
    pending_payment_bookings = []
    for booking in awaiting_verification:
        pending_payment = booking.payments.filter(verified=False).first()
        if pending_payment:
            pending_payment_bookings.append({
                'booking': booking,
                'pending_amount': pending_payment.amount
            })

    context = {
        'total_students': total_students,
        'prebooked': prebooked,
        'fully_paid': fully_paid,
        'expired': expired,
        'vacant_rooms': vacant_rooms,
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_rooms,
        'pending_payments': pending_payments,
        'total_pending_amount': float(total_pending_amount),
        'verified_payments_today': verified_payments_today,
        'recent_bookings': recent_bookings,
        'awaiting_verification': awaiting_verification,
        'expiring_soon': expiring_soon,
        'pending_payment_bookings': pending_payment_bookings,
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
def manage_bookings(request):
    if not request.user.is_staff:
        return redirect('student_dashboard')

    bookings = Booking.objects.select_related('student', 'room', 'room__hostel').prefetch_related('payments').order_by('-date_booked')
    all_rooms = Room.objects.select_related('hostel').order_by('hostel__name', 'room_number')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        bookings = bookings.filter(
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(student__reg_no__icontains=search_query) |
            Q(student__user__username__icontains=search_query)
        )

    if request.method == "POST":
        action = request.POST.get('action')
        booking_id = request.POST.get('booking_id')
        booking = Booking.objects.get(id=booking_id)

        # ✅ Mark payment verified
        if action == "verify":
            payment_id = request.POST.get('payment_id')
            if payment_id:
                payment = Payment.objects.get(id=payment_id, booking=booking)
            else:
                payment = booking.payments.filter(verified=False).first()
            
            if payment:
                payment.verified = True
                payment.save()
                # The signal will handle status update if fully paid
                messages.success(request, "Payment verified successfully.")

        # 🚪 Release room (cancel booking) - deprecated, use remove_student instead
        elif action == "release":
            room = booking.room
            booking.status = "expired"
            booking.save()
            if room:
                room.update_vacancy()
            
            # Process refund if payments exist
            total_paid = float(booking.get_total_paid_all())
            if total_paid > 0:
                FinanceTransaction.objects.create(
                    transaction_type='refund',
                    amount=total_paid,
                    booking=booking,
                    student=booking.student,
                    description=f"Refund for room release by admin - {room}",
                    status='completed',
                    date_completed=timezone.now()
                )
            
            # Send notification to student
            from .utils import send_notification
            subject = "Room Released by Admin"
            message = (
                f"Hello {booking.student.user.get_full_name()},\n\n"
                f"Your booking for {room} has been released by the administration.\n"
                f"Reason: Administrative action\n\n"
                f"All payments (Ksh {total_paid:,.2f}) have been refunded to the finance office.\n"
                f"You can use this refund for future bookings.\n\n"
                f"Thank you,\nANU Hostel Management"
            )
            send_notification(booking.student, subject, message)

            messages.info(request, f"Room released successfully. Refund of Ksh {total_paid:,.2f} processed.")
        
        # 👤 Remove student from room (new enhanced version)
        elif action == "remove_student":
            remove_action = request.POST.get('remove_action', 'cancel')  # 'cancel' or 'move'
            new_room_id = request.POST.get('new_room_id', None)
            reason = request.POST.get('reason', 'Administrative action')
            
            room = booking.room
            student = booking.student
            
            if remove_action == 'move' and new_room_id:
                # Move to another room
                try:
                    new_room = Room.objects.get(id=new_room_id)
                    if new_room.get_occupied_count() >= new_room.capacity:
                        messages.error(request, "Selected room is fully occupied.")
                        return redirect('manage_bookings')
                    
                    old_room = booking.room
                    booking.room = new_room
                    booking.save()
                    
                    if old_room:
                        old_room.update_vacancy()
                    new_room.update_vacancy()
                    
                    # Send notification
                    from .utils import send_notification
                    subject = "Room Assignment Changed by Admin"
                    message = (
                        f"Hello {student.user.get_full_name()},\n\n"
                        f"Your room assignment has been changed by the administration.\n"
                        f"Old Room: {old_room}\n"
                        f"New Room: {new_room.hostel.name} - Room {new_room.room_number}\n"
                        f"Room Type: {new_room.hostel.type}\n"
                        f"Room Price: Ksh {new_room.price:,.2f}\n"
                        f"Reason: {reason}\n\n"
                        f"Your booking details and payment progress remain unchanged.\n\n"
                        f"Thank you,\nANU Hostel Management"
                    )
                    send_notification(student, subject, message)
                    
                    messages.success(request, f"Student moved to {new_room}.")
                except Room.DoesNotExist:
                    messages.error(request, "Room not found.")
            else:
                # Cancel booking
                total_paid = float(booking.get_total_paid_all())
                
                booking.status = "expired"
                booking.save()
                
                if room:
                    room.update_vacancy()
                
                # Process refund
                if total_paid > 0:
                    FinanceTransaction.objects.create(
                        transaction_type='refund',
                        amount=total_paid,
                        booking=booking,
                        student=student,
                        description=f"Refund for room removal by admin - {room}. Reason: {reason}",
                        status='completed',
                        date_completed=timezone.now()
                    )
                
                # Send notification
                from .utils import send_notification
                subject = "Booking Cancelled by Admin"
                message = (
                    f"Hello {student.user.get_full_name()},\n\n"
                    f"Your booking for {room} has been cancelled by the administration.\n"
                    f"Reason: {reason}\n\n"
                )
                if total_paid > 0:
                    message += (
                        f"All payments (Ksh {total_paid:,.2f}) have been refunded to the finance office.\n"
                        f"You can use this refund for future bookings.\n\n"
                    )
                message += (
                    f"You can now book a new room from the available rooms page.\n\n"
                    f"Thank you,\nANU Hostel Management"
                )
                send_notification(student, subject, message)
                
                messages.success(request, f"Student removed from room. Refund of Ksh {total_paid:,.2f} processed.")

        # 🔄 Assign/Change room number
        elif action == "assign_room":
            new_room_id = request.POST.get('new_room_id')
            if new_room_id:
                try:
                    new_room = Room.objects.get(id=new_room_id)
                    old_room = booking.room
                    booking.room = new_room
                    booking.save()
                    if old_room:
                        old_room.update_vacancy()
                    new_room.update_vacancy()
                    
                    # Send notification to student
                    from .utils import send_notification
                    subject = "Room Assignment Updated"
                    message = (
                        f"Hello {booking.student.user.get_full_name()},\n\n"
                        f"Your room assignment has been updated by the administration.\n"
                        f"New Room: {new_room.hostel.name} - Room {new_room.room_number}\n"
                        f"Room Type: {new_room.hostel.type}\n"
                        f"Room Price: Ksh {new_room.price:,.2f}\n\n"
                        f"Your booking details and payment progress remain unchanged.\n\n"
                        f"Thank you,\nANU Hostel Management"
                    )
                    send_notification(booking.student, subject, message)
                    
                    messages.success(request, f"Room assigned: {new_room}")
                except Room.DoesNotExist:
                    messages.error(request, "Room not found.")

        return redirect('manage_bookings')

    context = {
        'bookings': bookings,
        'all_rooms': all_rooms,
        'search_query': search_query,
    }
    return render(request, 'manage_bookings.html', context)

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
        return redirect('admin_profile')
    
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('student_dashboard')
    
    user = request.user
    booking = Booking.objects.filter(student=student).order_by('-date_booked').first()

    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'update_profile':
            new_username = request.POST.get('username')
            new_phone = request.POST.get('phone')

            # Update username if changed
            if new_username and new_username != user.username:
                if User.objects.filter(username=new_username).exclude(id=user.id).exists():
                    messages.error(request, "Username already taken.")
                else:
                    user.username = new_username
                    user.save()

            # Update phone number
            if new_phone:
                student.phone = new_phone
                student.save()

            messages.success(request, "Profile updated successfully!")

        elif action == 'make_payment':
            if not booking:
                messages.error(request, "No active booking.")
                return redirect('student_profile')
            
            if booking.status == 'paid' or booking.is_fully_paid():
                messages.error(request, "Booking is already fully paid.")
                return redirect('student_profile')
            
            amount = request.POST.get('amount')
            try:
                amount = Decimal(amount)
                total_due = float(booking.get_total_due())
                paid_amount_all = float(booking.get_total_paid_all())  # Includes all payments
                remaining = total_due - paid_amount_all
                
                if amount <= 0:
                    messages.error(request, "Amount must be greater than 0.")
                else:
                    # Calculate available finance balance
                    total_refunded = FinanceTransaction.objects.filter(
                        student=student,
                        transaction_type='refund',
                        status='completed'
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                    
                    total_used_for_renewals = FinanceTransaction.objects.filter(
                        student=student,
                        transaction_type='renewal',
                        status='completed'
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                    
                    finance_available_balance = float(total_refunded - total_used_for_renewals)
                    
                    # Use finance balance first (automatically)
                    finance_to_use = min(float(remaining), finance_available_balance)
                    new_payment_needed = float(remaining) - finance_to_use
                    
                    # Calculate how much to use from new payment
                    actual_new_payment = min(float(amount), new_payment_needed)
                    total_payment_used = finance_to_use + actual_new_payment
                    
                    # Create payment from finance balance if any
                    finance_payment_amount = Decimal('0.00')
                    if finance_to_use > 0:
                        finance_payment_amount = Decimal(str(finance_to_use))
                        # Create payment record from finance
                        Payment.objects.create(
                            booking=booking,
                            amount=finance_payment_amount,
                            payment_type='full' if total_payment_used >= remaining else 'prepayment',
                            verified=True  # Auto-verify since it's from finance account
                        )
                        
                        # Create renewal transaction to record finance balance used
                        FinanceTransaction.objects.create(
                            transaction_type='renewal',
                            amount=finance_payment_amount,
                            booking=booking,
                            student=student,
                            description=f"Payment from finance balance - {booking.room.hostel.name if booking.room else 'N/A'} - Room {booking.room.room_number if booking.room else 'N/A'}",
                            status='completed',
                            date_completed=timezone.now()
                        )
                    
                    # Create payment from new payment if any
                    if actual_new_payment > 0:
                        Payment.objects.create(
                            booking=booking,
                            amount=Decimal(str(actual_new_payment)),
                            payment_type='full' if total_payment_used >= remaining else 'prepayment',
                            verified=False
                        )
                    
                    # Check if fully paid
                    new_total_paid = paid_amount_all + total_payment_used
                    if new_total_paid >= total_due:
                        booking.status = 'paid'
                        booking.save()
                        if booking.room:
                            booking.room.update_vacancy()
                    
                    # Handle excess payment (if amount > new_payment_needed)
                    excess = float(amount) - actual_new_payment
                    if excess > 0:
                        # Excess goes to finance as credit
                        FinanceTransaction.objects.create(
                            transaction_type='payment',
                            amount=Decimal(str(excess)),
                            booking=booking,
                            student=student,
                            description=f"Excess payment for {booking.room.hostel.name if booking.room else 'N/A'} - Room {booking.room.room_number if booking.room else 'N/A'} (credit to finance)",
                            status='completed',
                            date_completed=timezone.now()
                        )
                    
                    # Send notification
                    from .utils import send_notification
                    new_remaining = max(total_due - new_total_paid, 0)
                    
                    if new_total_paid >= total_due:
                        subject = "Payment Recorded - Fully Paid!"
                        message_parts = [
                            f"Hello {student.user.get_full_name()},\n\n",
                            f"Your payment has been processed successfully!\n\n"
                        ]
                        if finance_to_use > 0:
                            message_parts.append(f"From finance balance: Ksh {finance_to_use:,.2f}\n")
                        if actual_new_payment > 0:
                            message_parts.append(f"New payment: Ksh {actual_new_payment:,.2f}\n")
                        if excess > 0:
                            message_parts.append(f"Excess amount: Ksh {excess:,.2f} (credited to finance)\n")
                        message_parts.extend([
                            f"\nTotal paid: Ksh {new_total_paid:,.2f} / Ksh {total_due:,.2f}\n",
                            f"Room payment: Ksh {total_due:,.2f} (Fully Paid! 🎉)\n\n",
                            f"Your booking is now fully paid and confirmed!\n\n",
                            f"Thank you,\nANU Hostel Management"
                        ])
                        send_notification(student, subject, ''.join(message_parts))
                        
                        msg = f"Payment processed! Finance balance: Ksh {finance_to_use:,.2f}, New payment: Ksh {actual_new_payment:,.2f}. Booking fully paid!"
                        if excess > 0:
                            msg += f" Excess: Ksh {excess:,.2f} credited to finance."
                        messages.success(request, msg)
                    else:
                        subject = "Payment Recorded"
                        message_parts = [
                            f"Hello {student.user.get_full_name()},\n\n",
                            f"Your payment has been processed successfully!\n\n"
                        ]
                        if finance_to_use > 0:
                            message_parts.append(f"From finance balance: Ksh {finance_to_use:,.2f}\n")
                        if actual_new_payment > 0:
                            message_parts.append(f"New payment: Ksh {actual_new_payment:,.2f}\n")
                        message_parts.extend([
                            f"\nTotal paid so far: Ksh {new_total_paid:,.2f} / Ksh {total_due:,.2f}\n",
                            f"Remaining balance: Ksh {new_remaining:,.2f}\n\n"
                        ])
                        if actual_new_payment > 0:
                            message_parts.append("New payment is pending admin verification. You will be notified once it's verified.\n\n")
                        message_parts.append("Thank you,\nANU Hostel Management")
                        send_notification(student, subject, ''.join(message_parts))
                        
                        msg = f"Payment processed! Finance balance: Ksh {finance_to_use:,.2f}, New payment: Ksh {actual_new_payment:,.2f}. Remaining: Ksh {new_remaining:,.2f}"
                        messages.success(request, msg)
                        
            except (ValueError, TypeError) as e:
                messages.error(request, "Invalid amount.")
        
        elif action == 'pay_full_balance':
            if not booking:
                messages.error(request, "No active booking.")
                return redirect('student_profile')
            
            if booking.status == 'paid' or booking.is_fully_paid():
                messages.error(request, "Booking is already fully paid.")
                return redirect('student_profile')
            
            total_due = float(booking.get_total_due())
            paid_amount_all = float(booking.get_total_paid_all())  # Include all payments
            remaining = total_due - paid_amount_all
            
            if remaining > 0:
                # Calculate available finance balance
                total_refunded = FinanceTransaction.objects.filter(
                    student=student,
                    transaction_type='refund',
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                total_used_for_renewals = FinanceTransaction.objects.filter(
                    student=student,
                    transaction_type='renewal',
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                finance_available_balance = float(total_refunded - total_used_for_renewals)
                
                # Use finance balance first (automatically)
                finance_to_use = min(float(remaining), finance_available_balance)
                new_payment_needed = float(remaining) - finance_to_use
                
                # Create payment from finance balance if any
                if finance_to_use > 0:
                    finance_payment_amount = Decimal(str(finance_to_use))
                    Payment.objects.create(
                        booking=booking,
                        amount=finance_payment_amount,
                        payment_type='full',
                        verified=True  # Auto-verify since it's from finance account
                    )
                    
                    # Create renewal transaction
                    FinanceTransaction.objects.create(
                        transaction_type='renewal',
                        amount=finance_payment_amount,
                        booking=booking,
                        student=student,
                        description=f"Full payment from finance balance - {booking.room.hostel.name if booking.room else 'N/A'} - Room {booking.room.room_number if booking.room else 'N/A'}",
                        status='completed',
                        date_completed=timezone.now()
                    )
                
                # Create payment from new payment if needed
                if new_payment_needed > 0:
                    Payment.objects.create(
                        booking=booking,
                        amount=Decimal(str(new_payment_needed)),
                        payment_type='full',
                        verified=False
                    )
                
                # Update booking status and room vacancy
                new_total_paid = paid_amount_all + remaining
                booking.status = 'paid'
                booking.save()
                if booking.room:
                    booking.room.update_vacancy()
                
                # Send notification
                from .utils import send_notification
                subject = "Full Payment Recorded - Fully Paid!"
                message_parts = [
                    f"Hello {student.user.get_full_name()},\n\n",
                    f"Your full payment has been processed successfully!\n\n"
                ]
                if finance_to_use > 0:
                    message_parts.append(f"From finance balance: Ksh {finance_to_use:,.2f}\n")
                if new_payment_needed > 0:
                    message_parts.append(f"New payment: Ksh {new_payment_needed:,.2f}\n")
                message_parts.extend([
                    f"\nTotal paid: Ksh {new_total_paid:,.2f} / Ksh {total_due:,.2f}\n",
                    f"Room payment: Ksh {total_due:,.2f} (Fully Paid! 🎉)\n\n",
                    f"Your booking is now fully paid and confirmed!\n\n",
                    f"Thank you,\nANU Hostel Management"
                ])
                send_notification(student, subject, ''.join(message_parts))
                
                msg = f"Full payment processed! Finance balance: Ksh {finance_to_use:,.2f}, New payment: Ksh {new_payment_needed:,.2f}. Booking fully paid!"
                messages.success(request, msg)
            else:
                messages.info(request, "No remaining balance.")
        
        elif action == 'cancel_booking':
            if not booking:
                messages.error(request, "No active booking.")
                return redirect('student_profile')
            
            if booking.status == 'expired':
                messages.error(request, "Booking is already cancelled.")
                return redirect('student_profile')
            
            # Prevent cancellation if booking is fully paid - permanent until semester ends
            if booking.status == 'paid' or booking.is_fully_paid():
                messages.error(request, "Cannot cancel a fully paid booking. Your booking is permanent until the semester ends. You can renew or cancel at the end of the semester.")
                return redirect('student_profile')
            
            # Calculate refund amount - ALL payments (verified + unverified) go to finance
            total_paid = float(booking.get_total_paid_all())  # All payments for refund
            
            if total_paid > 0:
                # Create refund transaction
                FinanceTransaction.objects.create(
                    transaction_type='refund',
                    amount=total_paid,
                    booking=booking,
                    student=student,
                    description=f"Refund for cancelled booking - {booking.room}",
                    status='completed',
                    date_completed=timezone.now()
                )
                
                # Mark all payments as refunded (set booking to expired)
                booking.status = 'expired'
                booking.save()
                
                # Update room vacancy
                if booking.room:
                    booking.room.update_vacancy()
                
                # Notify student
                from .utils import send_notification
                subject = "Booking Cancelled - Refund Processed"
                message = (
                    f"Hello {student.user.get_full_name()},\n\n"
                    f"Your booking for {booking.room} has been cancelled.\n"
                    f"All payments (Ksh {total_paid:,.2f}) have been refunded to the finance office.\n"
                    f"This amount can be used for future bookings when you prebook a new room.\n\n"
                    f"Thank you,\nANU Hostel Management"
                )
                send_notification(student, subject, message)
                
                messages.success(request, f"Booking cancelled. All payments (Ksh {total_paid:,.2f}) refunded to finance office and available for future bookings.")
            else:
                # No payment made, just cancel
                booking.status = 'expired'
                booking.save()
                
                if booking.room:
                    booking.room.update_vacancy()
                
                # Send notification
                from .utils import send_notification
                subject = "Booking Cancelled"
                message = (
                    f"Hello {student.user.get_full_name()},\n\n"
                    f"Your booking for {booking.room} has been cancelled successfully.\n"
                    f"No refund is applicable as no payments were made.\n\n"
                    f"Thank you,\nANU Hostel Management"
                )
                send_notification(student, subject, message)
                
                messages.success(request, "Booking cancelled successfully.")
        
        elif action == 'change_room':
            if not booking:
                messages.error(request, "No active booking.")
                return redirect('student_profile')
            
            if booking.status == 'paid' or booking.is_fully_paid():
                messages.error(request, "Cannot change room. Your booking is fully paid and permanent until the semester ends. Please cancel and rebook, or wait until semester end to renew.")
                return redirect('student_profile')
            
            new_room_id = request.POST.get('new_room_id')
            if new_room_id:
                try:
                    new_room = Room.objects.get(id=new_room_id)
                    old_room = booking.room
                    
                    # Check if new room is available
                    if not new_room.is_vacant and new_room.get_occupied_count() >= new_room.capacity:
                        messages.error(request, "Selected room is fully occupied.")
                        return redirect('student_profile')
                    
                    # Check gender compatibility
                    if student.gender and new_room.hostel.gender.lower() != student.gender.lower():
                        messages.error(request, "Cannot book room for different gender.")
                        return redirect('student_profile')
                    
                    booking.room = new_room
                    booking.save()
                    
                    # Update room vacancies
                    if old_room:
                        old_room.update_vacancy()
                    new_room.update_vacancy()
                    
                    # Send notification
                    from .utils import send_notification
                    subject = "Room Changed"
                    message = (
                        f"Hello {student.user.get_full_name()},\n\n"
                        f"Your room has been changed successfully.\n"
                        f"New Room: {new_room.hostel.name} - Room {new_room.room_number}\n"
                        f"Room Type: {new_room.hostel.type}\n"
                        f"Room Price: Ksh {new_room.price:,.2f}\n\n"
                        f"Your payment progress has been maintained. "
                        f"Current balance: Ksh {booking.get_total_due() - booking.get_total_paid():,.2f}\n\n"
                        f"Thank you,\nANU Hostel Management"
                    )
                    send_notification(student, subject, message)
                    
                    messages.success(request, f"Room changed to {new_room.hostel.name} - Room {new_room.room_number}")
                except Room.DoesNotExist:
                    messages.error(request, "Room not found.")

    # Calculate Finance Account Balance for transparency
    total_refunded = FinanceTransaction.objects.filter(
        student=student,
        transaction_type='refund',
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_used_for_renewals = FinanceTransaction.objects.filter(
        student=student,
        transaction_type='renewal',
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    finance_available_balance = total_refunded - total_used_for_renewals
    finance_available_balance_float = float(finance_available_balance)
    
    context = {
        'student': student,
        'booking': booking,
        'finance_total_refunded': float(total_refunded),
        'finance_total_used': float(total_used_for_renewals),
        'finance_available_balance': finance_available_balance_float,
    }
    
    if booking:
        if booking.room:
            total_due = float(booking.get_total_due())
            # Use get_total_paid_all() to include unverified payments for student display
            paid_amount = float(booking.get_total_paid_all())  # Includes all payments (verified + unverified)
            remaining = max(total_due - paid_amount, 0)
        else:
            total_due = 0
            paid_amount = 0
            remaining = 0
        
        # Calculate how much finance balance will be used and new payment needed
        finance_to_use = min(remaining, finance_available_balance_float) if booking.room and remaining > 0 else 0
        new_payment_needed = max(remaining - finance_to_use, 0)
        
        # Get available rooms for changing (same gender, vacant)
        available_rooms = Room.objects.none()
        if booking.room:
            gender = (student.gender or "male").lower()
            hostels = (
                Hostel.objects.filter(gender="Male") if gender == "male"
                else Hostel.objects.filter(gender="Female")
            )
            available_rooms = Room.objects.filter(hostel__in=hostels, is_vacant=True).exclude(id=booking.room.id)
        
        context.update({
            'total_due': total_due,
            'paid_amount': paid_amount,
            'remaining': remaining,
            'payments': booking.payments.all().order_by('-date_paid'),
            'available_rooms': available_rooms,
            'finance_to_use': finance_to_use,
            'new_payment_needed': new_payment_needed,
        })
    
    return render(request, 'student_profile.html', context)

@login_required
def admin_profile(request):
    if not request.user.is_staff:
        return redirect('student_profile')
    
    user = request.user

    if request.method == "POST":
        new_username = request.POST.get('username')
        new_email = request.POST.get('email')

        # Update username if changed
        if new_username and new_username != user.username:
            if User.objects.filter(username=new_username).exclude(id=user.id).exists():
                messages.error(request, "Username already taken.")
            else:
                user.username = new_username
                user.save()

        # Update email
        if new_email:
            user.email = new_email
            user.save()

        messages.success(request, "Profile updated successfully!")

    return render(request, 'admin_profile.html', {'user': user})

@login_required
def view_roommates(request):
    """View roommates - only accessible if booking is fully paid."""
    if request.user.is_staff:
        return redirect('admin_dashboard')
    
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('student_dashboard')
    
    booking = Booking.objects.filter(student=student).order_by('-date_booked').first()
    
    if not booking:
        messages.warning(request, "You have no active booking.")
        return redirect('student_dashboard')
    
    if not booking.is_fully_paid():
        messages.warning(request, "You can only view roommates after fully paying for your room.")
        return redirect('student_profile')
    
    roommates = booking.get_roommates()
    
    return render(request, 'roommates.html', {
        'booking': booking,
        'roommates': roommates,
    })

@login_required
def view_room_details(request, room_id):
    """View detailed information about a room."""
    if request.user.is_staff:
        return redirect('admin_dashboard')
    
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('student_dashboard')
    
    room = get_object_or_404(Room, id=room_id)
    
    # Check if student has access to this room (same gender)
    gender = (student.gender or "male").lower()
    if room.hostel.gender.lower() != gender:
        messages.error(request, "You don't have access to view this room.")
        return redirect('student_dashboard')
    
    # Get roommates if any (only fully paid students)
    roommates = Booking.objects.filter(room=room, status='paid').select_related('student__user')
    
    # Calculate occupancy (includes both prebooked and paid)
    occupied_count = room.get_occupied_count()
    available_spots = max(0, room.capacity - occupied_count)
    
    context = {
        'room': room,
        'roommates': roommates,
        'student': student,
        'occupied_count': occupied_count,
        'available_spots': available_spots,
    }
    
    return render(request, 'room_details.html', context)

@login_required
def finance_dashboard(request):
    """Finance office dashboard to view all transactions and manage renewals."""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Finance dashboard is for staff only.")
        return redirect('student_dashboard')
    
    # Search functionality for individual students
    search_query = request.GET.get('search', '')
    selected_student_id = request.GET.get('student_id', '')
    
    # Get all students for search dropdown
    all_students = Student.objects.select_related('user').all().order_by('user__first_name', 'user__last_name')
    
    selected_student = None
    student_finance_data = None
    
    if selected_student_id:
        try:
            selected_student = Student.objects.get(id=selected_student_id)
            # Calculate student-specific finance data
            student_total_refunded = FinanceTransaction.objects.filter(
                student=selected_student,
                transaction_type='refund',
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            student_total_used = FinanceTransaction.objects.filter(
                student=selected_student,
                transaction_type='renewal',
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            student_available_balance = student_total_refunded - student_total_used
            
            student_finance_data = {
                'total_refunded': float(student_total_refunded),
                'total_used': float(student_total_used),
                'available_balance': float(student_available_balance),
            }
        except Student.DoesNotExist:
            pass
    
    # Handle renewal/rebook action
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'process_renewal':
            booking_id = request.POST.get('booking_id')
            renewal_amount = request.POST.get('renewal_amount')
            
            try:
                booking = Booking.objects.get(id=booking_id)
                renewal_amount = Decimal(renewal_amount)
                
                # Check if finance has enough balance
                total_received = FinanceTransaction.objects.filter(
                    transaction_type='payment',
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                total_refunded = FinanceTransaction.objects.filter(
                    transaction_type='refund',
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                total_renewals = FinanceTransaction.objects.filter(
                    transaction_type='renewal',
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                net_amount = total_received - total_refunded - total_renewals
                
                if renewal_amount > net_amount:
                    messages.error(request, f"Insufficient funds. Available balance: Ksh {net_amount:,.2f}")
                elif booking.status != 'expired':
                    messages.error(request, "Can only process renewal for expired bookings.")
                else:
                    # Reactivate the booking
                    total_due = float(booking.get_total_due())
                    if renewal_amount >= total_due:
                        booking.status = 'paid'
                    else:
                        booking.status = 'prebooked'
                    
                    booking.save()
                    
                    # Update room vacancy
                    if booking.room:
                        booking.room.update_vacancy()
                    
                    # Create payment transaction from finance account
                    from .models import Payment
                    Payment.objects.create(
                        booking=booking,
                        amount=renewal_amount,
                        payment_type='full' if renewal_amount >= total_due else 'prepayment',
                        verified=True  # Auto-verify since it's from finance account
                    )
                    
                    # Create finance transaction to record money used from finance account for renewal
                    FinanceTransaction.objects.create(
                        transaction_type='renewal',  # Money used from finance account
                        amount=renewal_amount,
                        booking=booking,
                        student=booking.student,
                        description=f"Renewal payment processed from finance account - {booking.room.hostel.name} - Room {booking.room.room_number}",
                        status='completed',
                        date_completed=timezone.now()
                    )
                    
                    # Notify student
                    from .utils import send_notification
                    subject = "Room Renewal Processed"
                    message = (
                        f"Hello {booking.student.user.get_full_name()},\n\n"
                        f"Your room renewal has been processed successfully.\n"
                        f"Room: {booking.room.hostel.name} - Room {booking.room.room_number}\n"
                        f"Payment: Ksh {renewal_amount:,.2f} (processed from finance account)\n"
                        f"Status: {'Fully Paid' if booking.status == 'paid' else 'Pre-booked'}\n\n"
                        f"Your booking is now active. Thank you!\n\n"
                        f"ANU Hostel Management"
                    )
                    send_notification(booking.student, subject, message)
                    
                    messages.success(request, f"Renewal payment of Ksh {renewal_amount:,.2f} processed successfully. Booking reactivated.")
            except (Booking.DoesNotExist, ValueError) as e:
                messages.error(request, "Invalid booking or amount.")
    
    transactions = FinanceTransaction.objects.select_related('student__user', 'booking__room').order_by('-date_created')
    
    # Calculate totals
    total_received = FinanceTransaction.objects.filter(
        transaction_type='payment',
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_refunded = FinanceTransaction.objects.filter(
        transaction_type='refund',
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_renewals = FinanceTransaction.objects.filter(
        transaction_type='renewal',
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Net amount = received - refunded - renewals (money used from account)
    net_amount = total_received - total_refunded - total_renewals
    
    # Pending transactions
    pending_payments = FinanceTransaction.objects.filter(
        transaction_type='payment',
        status='pending'
    ).count()
    
    pending_refunds = FinanceTransaction.objects.filter(
        transaction_type='refund',
        status='pending'
    ).count()
    
    # Get expired bookings that can be renewed (students with expired bookings who want to rebook same room)
    expired_bookings = Booking.objects.filter(
        status='expired'
    ).select_related('student__user', 'room').order_by('-date_booked')[:20]
    
    # Get recent payments and refunds for quick view (global, not filtered)
    recent_payments = FinanceTransaction.objects.filter(
        transaction_type='payment',
        status='completed'
    ).select_related('student__user', 'booking__room').order_by('-date_created')[:10]
    
    recent_refunds = FinanceTransaction.objects.filter(
        transaction_type='refund',
        status='completed'
    ).select_related('student__user', 'booking__room').order_by('-date_created')[:10]
    
    # Get student transactions if student selected
    student_transactions = None
    if selected_student:
        student_transactions = FinanceTransaction.objects.filter(
            student=selected_student
        ).select_related('booking__room').order_by('-date_created')
    
    context = {
        'transactions': transactions,
        'total_received': float(total_received),
        'total_refunded': float(total_refunded),
        'total_renewals': float(total_renewals),
        'net_amount': float(net_amount),
        'pending_payments': pending_payments,
        'pending_refunds': pending_refunds,
        'expired_bookings': expired_bookings,
        'recent_payments': recent_payments,
        'recent_refunds': recent_refunds,
        'all_students': all_students,
        'selected_student': selected_student,
        'student_finance_data': student_finance_data,
        'student_transactions': student_transactions,
        'search_query': search_query,
        'selected_student_id': selected_student_id,
    }
    
    return render(request, 'finance_dashboard.html', context)

@login_required
def available_rooms(request):
    student = Student.objects.get(user=request.user)
    gender = (student.gender or "male").lower()

    # Get current bookings
    active_booking = Booking.objects.filter(student=student, status__in=['prebooked', 'paid']).first()
    expired_booking = Booking.objects.filter(student=student, status='expired').order_by('-date_booked').first()
    
    # Check if booking is fully paid
    is_fully_paid = False
    if active_booking:
        is_fully_paid = (active_booking.status == 'paid' or active_booking.is_fully_paid())

    # Gender-based hostel filtering
    hostels = (
        Hostel.objects.filter(gender="Male") if gender == "male"
        else Hostel.objects.filter(gender="Female")
    )

    # Get all rooms (vacant or not, for display)
    all_rooms = Room.objects.filter(hostel__in=hostels).order_by('hostel__name', 'room_number')
    
    # Group rooms by hostel and add occupied count
    rooms_by_hostel = {}
    for room in all_rooms:
        hostel_name = room.hostel.name
        if hostel_name not in rooms_by_hostel:
            rooms_by_hostel[hostel_name] = []
        # Add occupied count as attribute for template
        room.occupied_count = room.get_occupied_count()
        room.is_available = room.occupied_count < room.capacity
        rooms_by_hostel[hostel_name].append(room)

    # Handle POST requests
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "prebook":
            room_id = request.POST.get("room_id")
            # Fixed prebooking amount of 2500
            prebook_amount = Decimal('2500.00')
            
            try:
                room = Room.objects.get(id=room_id)
                
                # Check if room is available (not fully occupied)
                if room.get_occupied_count() >= room.capacity:
                    messages.error(request, "This room is fully occupied.")
                    return redirect('available_rooms')

                # Check if booking is fully paid - cannot switch if fully paid
                if active_booking:
                    if active_booking.status == 'paid' or active_booking.is_fully_paid():
                        messages.error(request, "Cannot switch rooms. Your current booking is fully paid and permanent until the semester ends.")
                        return redirect('available_rooms')
                
                # Track if we're cancelling a booking and how much refund is available
                refund_from_cancellation = Decimal('0.00')
                prebook_amount_to_use = Decimal('0.00')
                
                # If student has active booking, cancel it first
                if active_booking:
                    # Cancel existing booking and process refund - ALL payments (verified + unverified)
                    total_paid = float(active_booking.get_total_paid_all())  # All payments
                    refund_from_cancellation = Decimal(str(total_paid))
                    
                    if total_paid > 0:
                        # Create refund transaction for ALL payments
                        FinanceTransaction.objects.create(
                            transaction_type='refund',
                            amount=refund_from_cancellation,
                            booking=active_booking,
                            student=student,
                            description=f"Refund for cancelled booking (switching rooms) - {active_booking.room}. All payments refunded: Ksh {total_paid:,.2f}",
                            status='completed',
                            date_completed=timezone.now()
                        )
                    
                    # Mark old booking as expired
                    active_booking.status = 'expired'
                    active_booking.save()
                    
                    # Update old room vacancy
                    if active_booking.room:
                        active_booking.room.update_vacancy()
                
                # Check student's available refund balance in finance
                # Sum of all refunds minus renewals for this student (includes the refund we just created)
                total_refunded = FinanceTransaction.objects.filter(
                    student=student,
                    transaction_type='refund',
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                total_used_for_renewals = FinanceTransaction.objects.filter(
                    student=student,
                    transaction_type='renewal',
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                available_balance = total_refunded - total_used_for_renewals
                
                # Use available refund balance for prebooking (use 2500 or available balance, whichever is less)
                if available_balance > 0:
                    prebook_amount_to_use = min(Decimal('2500.00'), available_balance)
                    
                    if prebook_amount_to_use > 0:
                        # Create renewal transaction for the amount used from refund
                        FinanceTransaction.objects.create(
                            transaction_type='renewal',
                            amount=prebook_amount_to_use,
                            student=student,
                            description=f"Automatic prebooking payment from refund balance - {room.hostel.name} - Room {room.room_number}",
                            status='completed',
                            date_completed=timezone.now()
                        )
                
                # Create new booking
                booking = Booking.objects.create(student=student, room=room, status="prebooked")
                
                # Create payment with fixed 2500 amount
                total_due = float(room.price)
                if float(prebook_amount) > total_due:
                    # Excess payment - create two payments: one for room, one as excess to finance
                    Payment.objects.create(
                        booking=booking,
                        amount=total_due,
                        payment_type='full',
                        verified=False
                    )
                    
                    # Excess goes to finance as a credit
                    excess = float(prebook_amount) - total_due
                    FinanceTransaction.objects.create(
                        transaction_type='payment',
                        amount=excess,
                        booking=booking,
                        student=student,
                        description=f"Excess payment for {room.hostel.name} - Room {room.room_number} (credit to finance)",
                        status='completed',
                        date_completed=timezone.now()
                    )
                    
                    booking.status = 'paid'
                    booking.save()
                else:
                    Payment.objects.create(
                        booking=booking,
                        amount=prebook_amount,
                        payment_type='prepayment',  # Always prepayment for fixed 2500
                        verified=False
                    )
                
                # Update room vacancy
                room.update_vacancy()
                
                # Send notification
                from .utils import send_notification
                remaining = max(float(total_due) - float(prebook_amount), 0)
                subject = "Hostel Pre-booking Confirmation"
                
                # Check if refund balance was used - check available_balance from above
                refund_info = ""
                try:
                    # available_balance and prebook_amount_to_use are defined in the try block above
                    if available_balance > 0 and prebook_amount_to_use > 0:
                        refund_info = f"\nNote: Ksh {float(prebook_amount_to_use):,.2f} was automatically used from your refund balance (Ksh {float(available_balance):,.2f} available).\n"
                except NameError:
                    # Variables don't exist (no active booking to cancel), so no refund used
                    pass
                
                if float(prebook_amount) > total_due:
                    message = (
                        f"Dear {student.user.get_full_name()},\n\n"
                        f"You have successfully pre-booked {room.hostel.name} - Room {room.room_number}.\n"
                        f"Room Type: {room.hostel.type}\n"
                        f"Total Amount Due: Ksh {total_due:,.2f}\n"
                        f"Payment Made: Ksh {prebook_amount:,.2f}\n"
                        f"Excess Amount: Ksh {float(prebook_amount) - total_due:,.2f} (credited to finance account)\n{refund_info}\n"
                        f"Your booking is fully paid! 🎉\n\n"
                        f"Thank you,\nANU Hostel Management System"
                    )
                else:
                    message = (
                        f"Dear {student.user.get_full_name()},\n\n"
                        f"You have successfully pre-booked {room.hostel.name} - Room {room.room_number}.\n"
                        f"Room Type: {room.hostel.type}\n"
                        f"Total Amount Due: Ksh {total_due:,.2f}\n"
                        f"Prepayment Made: Ksh {prebook_amount:,.2f}\n{refund_info}"
                        f"Remaining Balance: Ksh {remaining:,.2f}\n\n"
                        f"Please complete the remaining payment before reporting week. "
                        f"You can make payments from your payments page.\n\n"
                        f"Thank you,\nANU Hostel Management System"
                    )
                send_notification(student, subject, message)

                messages.success(request, f"You have successfully pre-booked {room.hostel.name} - {room.room_number}.")
                return redirect('student_dashboard')

            except (Room.DoesNotExist, ValueError) as e:
                messages.error(request, "Invalid room or amount.")
        
        elif action == "cancel_and_prebook":
            # This is handled in the prebook action above when active_booking exists
            # Just redirect to show available rooms
            return redirect('available_rooms')
        
        elif action == "renew_room":
            booking_id = request.POST.get("booking_id")
            try:
                booking = Booking.objects.get(id=booking_id, student=student, status='expired')
                
                if not booking.room:
                    messages.error(request, "No room assigned to this booking.")
                    return redirect('available_rooms')
                
                # Check if room is still available
                if booking.room.get_occupied_count() >= booking.room.capacity:
                    messages.error(request, "This room is now fully occupied. Please select a different room.")
                    return redirect('available_rooms')
                
                # Reactivate booking
                booking.status = 'prebooked'
                booking.save()
                
                # Update room vacancy
                booking.room.update_vacancy()
                
                # Create payment of 2500 from finance (assuming refund was processed)
                Payment.objects.create(
                    booking=booking,
                    amount=2500,
                    payment_type='prepayment',
                    verified=False
                )
                
                # Create finance transaction for renewal
                FinanceTransaction.objects.create(
                    transaction_type='renewal',
                    amount=Decimal('2500.00'),
                    booking=booking,
                    student=student,
                    description=f"Renewal prebooking payment - {booking.room.hostel.name} - Room {booking.room.room_number}",
                    status='completed',
                    date_completed=timezone.now()
                )
                
                # Send notification
                from .utils import send_notification
                subject = "Room Renewed"
                message = (
                    f"Dear {student.user.get_full_name()},\n\n"
                    f"Your room has been renewed successfully.\n"
                    f"Room: {booking.room.hostel.name} - Room {booking.room.room_number}\n"
                    f"Prepayment: Ksh 2,500.00\n"
                    f"Remaining Balance: Ksh {float(booking.room.price) - 2500:,.2f}\n\n"
                    f"Please complete the remaining payment.\n\n"
                    f"Thank you,\nANU Hostel Management System"
                )
                send_notification(student, subject, message)
                
                messages.success(request, "Room renewed successfully!")
                return redirect('student_dashboard')
                
            except Booking.DoesNotExist:
                messages.error(request, "Invalid booking.")

    # Filter available rooms (for expired booking case) - rooms that are not fully occupied
    available_rooms_for_booking = []
    for room in Room.objects.filter(hostel__in=hostels):
        occupied_count = room.get_occupied_count()
        if occupied_count < room.capacity:
            if not (expired_booking and expired_booking.room and room.id == expired_booking.room.id):
                room.occupied_count = occupied_count
                room.is_available = True
                available_rooms_for_booking.append(room)
    
    # Get all available rooms for filter dropdowns
    all_available_rooms = []
    for room_list in rooms_by_hostel.values():
        for room in room_list:
            if room.is_available:
                all_available_rooms.append(room)
    
    # Get hostel names for filter
    hostel_names = list(rooms_by_hostel.keys())

    context = {
        'rooms_by_hostel': rooms_by_hostel,
        'active_booking': active_booking,
        'expired_booking': expired_booking,
        'available_rooms_for_booking': available_rooms_for_booking,
        'all_available_rooms': all_available_rooms,
        'hostel_names': hostel_names,
        'is_fully_paid': is_fully_paid,
    }
    
    return render(request, 'available_rooms.html', context)

@login_required
def mark_notification_as_read(request, notification_id):
    """Mark a single notification as read."""
    if request.user.is_staff:
        messages.error(request, "Admins cannot mark student notifications as read.")
        return redirect('admin_dashboard')
    
    student = get_object_or_404(Student, user=request.user)
    notification = get_object_or_404(Notification, id=notification_id, student=student)
    notification.is_read = True
    notification.save()
    messages.success(request, "Notification marked as read.")
    return redirect(request.META.get('HTTP_REFERER', 'notifications_page'))


@login_required
def mark_all_notifications_as_read(request):
    """Mark all notifications as read for the logged-in student."""
    if request.user.is_staff:
        messages.error(request, "Admins cannot mark student notifications as read.")
        return redirect('admin_dashboard')
    
    student = get_object_or_404(Student, user=request.user)
    updated_count = Notification.objects.filter(student=student, is_read=False).update(is_read=True)
    if updated_count > 0:
        messages.success(request, f"Marked {updated_count} notification(s) as read.")
    else:
        messages.info(request, "All notifications are already read.")
    return redirect(request.META.get('HTTP_REFERER', 'notifications_page'))

# -----------------------------
# NOTIFICATIONS PAGE
# -----------------------------
@login_required
def notifications_page(request):
    # Student notifications page
    if request.user.is_staff:
        return redirect('admin_notifications_page')

    student = get_object_or_404(Student, user=request.user)

    qs = Notification.objects.filter(student=student).order_by('-date_sent')
    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Don't auto-mark as read - let users control it
    total_unread = qs.filter(is_read=False).count()

    return render(request, 'notifications.html', {
        'page_obj': page_obj,
        'total_unread': total_unread,
    })

# -----------------------------
# ADMIN NOTIFICATIONS PAGE
# -----------------------------
@login_required
def admin_notifications_page(request):
    if not request.user.is_staff:
        return redirect('student_dashboard')

    # Get bookings awaiting verification (prebooked with unverified payments)
    awaiting_verification = Booking.objects.filter(
        status='prebooked',
        payments__verified=False
    ).distinct().select_related('student', 'room', 'room__hostel').order_by('-date_booked')[:20]

    # Recent bookings (all statuses)
    recent_bookings = Booking.objects.select_related('student', 'room', 'room__hostel').order_by('-date_booked')[:20]

    # Recent payments (verified and unverified)
    recent_payments = Payment.objects.select_related('booking', 'booking__student', 'booking__room', 'booking__room__hostel').order_by('-date_paid')[:20]

    # Statistics
    total_prebooked = Booking.objects.filter(status='prebooked').count()
    total_fully_paid = Booking.objects.filter(status='paid').count()
    total_expired = Booking.objects.filter(status='expired').count()
    pending_payments_count = Payment.objects.filter(verified=False).count()
    
    # Rooms statistics
    total_rooms = Room.objects.count()
    vacant_rooms = Room.objects.filter(is_vacant=True).count()
    occupied_rooms = total_rooms - vacant_rooms

    context = {
        'awaiting_verification': awaiting_verification,
        'recent_bookings': recent_bookings,
        'recent_payments': recent_payments,
        'total_prebooked': total_prebooked,
        'total_fully_paid': total_fully_paid,
        'total_expired': total_expired,
        'pending_payments_count': pending_payments_count,
        'total_rooms': total_rooms,
        'vacant_rooms': vacant_rooms,
        'occupied_rooms': occupied_rooms,
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
        country_code = request.POST.get('country_code', '+254')  # Default to Kenya
        gender = request.POST.get('gender')
        course = request.POST.get('course')
        year_of_study = request.POST.get('year_of_study')

        if not all([username, password, reg_no, phone, gender, course, year_of_study]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('register')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')
        
        if Student.objects.filter(reg_no=reg_no).exists():
            messages.error(request, 'Registration number already exists.')
            return redirect('register')

        # Validate phone number length based on country code
        phone_lengths = {
            '+254': (9, 9),   # Kenya
            '+255': (9, 9),   # Tanzania
            '+256': (9, 9),   # Uganda
            '+250': (9, 9),   # Rwanda
            '+233': (9, 9),   # Ghana
            '+234': (10, 10), # Nigeria
            '+1': (10, 10),   # US/Canada
            '+44': (10, 10),  # UK
            '+27': (9, 9),    # South Africa
            '+91': (10, 10),  # India
            '+86': (11, 11),  # China
            '+81': (10, 10),  # Japan
            '+61': (9, 9),    # Australia
            '+49': (10, 11),  # Germany
            '+33': (9, 9),    # France
            '+39': (9, 10),   # Italy
            '+34': (9, 9),    # Spain
            '+31': (9, 9),    # Netherlands
            '+32': (9, 9),    # Belgium
            '+41': (9, 9),    # Switzerland
            '+46': (9, 9),    # Sweden
            '+47': (8, 8),    # Norway
            '+45': (8, 8),    # Denmark
            '+358': (9, 10),  # Finland
            '+351': (9, 9),   # Portugal
            '+30': (10, 10),  # Greece
            '+353': (9, 9),   # Ireland
            '+64': (8, 9),    # New Zealand
            '+52': (10, 10),  # Mexico
            '+55': (10, 11),  # Brazil
            '+54': (10, 10),  # Argentina
            '+57': (10, 10),  # Colombia
            '+60': (9, 10),   # Malaysia
            '+65': (8, 8),    # Singapore
            '+66': (9, 9),    # Thailand
            '+84': (9, 10),   # Vietnam
            '+62': (9, 11),   # Indonesia
            '+63': (10, 10),  # Philippines
        }
        
        phone_len = len(phone) if phone else 0
        if country_code in phone_lengths:
            min_len, max_len = phone_lengths[country_code]
            if phone_len < min_len or phone_len > max_len:
                messages.error(request, f'Phone number must be {min_len}{"-" + str(max_len) if min_len != max_len else ""} digits for {country_code}.')
                return redirect('register')
        else:
            # Generic validation for countries not in list
            if phone_len < 7 or phone_len > 15:
                messages.error(request, 'Phone number must be between 7 and 15 digits.')
                return redirect('register')
        
        # Validate phone contains only digits
        if not phone.isdigit():
            messages.error(request, 'Phone number must contain only digits.')
            return redirect('register')

        # Combine country code with phone number
        full_phone = f"{country_code}{phone}" if phone else ''

        user = User.objects.create_user(username=username, password=password,
                                        first_name=first_name or '', last_name=last_name or '')
        Student.objects.create(user=user, reg_no=reg_no, phone=full_phone, gender=gender,
                               course=course, year_of_study=year_of_study)
        messages.success(request, 'Account created successfully! Please log in.')
        return redirect('login')

    return render(request, 'register.html')


# -----------------------------
# ROOM MANAGEMENT (Admin)
# -----------------------------
@login_required
def manage_rooms(request):
    if not request.user.is_staff:
        return redirect('student_dashboard')
    
    hostels = Hostel.objects.all().order_by('name')
    rooms = Room.objects.select_related('hostel').order_by('hostel__name', 'room_number')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_room':
            hostel_id = request.POST.get('hostel_id')
            room_number = request.POST.get('room_number')
            capacity = request.POST.get('capacity', 2)
            price = request.POST.get('price')
            description = request.POST.get('description', '')
            
            try:
                hostel = Hostel.objects.get(id=hostel_id)
                if Room.objects.filter(hostel=hostel, room_number=room_number).exists():
                    messages.error(request, f"Room {room_number} already exists in {hostel.name}.")
                else:
                    Room.objects.create(
                        hostel=hostel,
                        room_number=room_number,
                        capacity=int(capacity),
                        price=Decimal(price),
                        description=description
                    )
                    messages.success(request, f"Room {room_number} added to {hostel.name}.")
            except (Hostel.DoesNotExist, ValueError) as e:
                messages.error(request, "Invalid data. Please check all fields.")
        
        elif action == 'edit_room':
            room_id = request.POST.get('room_id')
            room_number = request.POST.get('room_number')
            capacity = request.POST.get('capacity')
            price = request.POST.get('price')
            description = request.POST.get('description', '')
            
            try:
                room = Room.objects.get(id=room_id)
                # Check if room number conflicts with another room in same hostel
                if room_number != room.room_number:
                    if Room.objects.filter(hostel=room.hostel, room_number=room_number).exists():
                        messages.error(request, f"Room {room_number} already exists in {room.hostel.name}.")
                        return redirect('manage_rooms')
                
                old_price = room.price
                old_description = room.description
                old_room_number = room.room_number
                old_capacity = room.capacity
                
                room.room_number = room_number
                room.capacity = int(capacity)
                room.price = Decimal(price)
                room.description = description
                room.save()
                room.update_vacancy()  # Update vacancy status
                
                # Notify students with active bookings in this room about changes
                active_bookings = Booking.objects.filter(room=room, status__in=['prebooked', 'paid'])
                if active_bookings.exists():
                    from .utils import send_notification
                    changes = []
                    if old_room_number != room_number:
                        changes.append(f"Room number changed from {old_room_number} to {room_number}")
                    if old_price != Decimal(price):
                        changes.append(f"Price changed from Ksh {old_price:,.2f} to Ksh {Decimal(price):,.2f}")
                    if old_capacity != int(capacity):
                        changes.append(f"Capacity changed from {old_capacity} to {capacity}")
                    if old_description != description:
                        changes.append("Room description updated")
                    
                    # Always notify if any changes or just to confirm update
                    for booking in active_bookings:
                        subject = "Room Details Updated by Admin"
                        if changes:
                            message = (
                                f"Hello {booking.student.user.get_full_name()},\n\n"
                                f"Your room ({room.hostel.name} - Room {room_number}) has been updated by the administration.\n\n"
                                f"Changes:\n" + "\n".join(f"• {change}" for change in changes) + "\n\n"
                                f"Updated Room Details:\n"
                                f"• Room Number: {room_number}\n"
                                f"• Capacity: {capacity}\n"
                                f"• Price: Ksh {Decimal(price):,.2f}\n"
                                f"• Description: {description or 'No description'}\n\n"
                                f"Your booking and payment progress remain unchanged.\n\n"
                                f"Thank you,\nANU Hostel Management"
                            )
                        else:
                            message = (
                                f"Hello {booking.student.user.get_full_name()},\n\n"
                                f"Your room ({room.hostel.name} - Room {room_number}) details have been updated by the administration.\n\n"
                                f"Updated Room Details:\n"
                                f"• Room Number: {room_number}\n"
                                f"• Capacity: {capacity}\n"
                                f"• Price: Ksh {Decimal(price):,.2f}\n"
                                f"• Description: {description or 'No description'}\n\n"
                                f"Your booking and payment progress remain unchanged.\n\n"
                                f"Thank you,\nANU Hostel Management"
                            )
                        send_notification(booking.student, subject, message)
                
                messages.success(request, f"Room {room_number} updated successfully.")
            except (Room.DoesNotExist, ValueError) as e:
                messages.error(request, "Invalid data. Please check all fields.")
        
        elif action == 'delete_room':
            room_id = request.POST.get('room_id')
            try:
                room = Room.objects.get(id=room_id)
                # Check if room has active bookings
                active_bookings = Booking.objects.filter(room=room, status__in=['prebooked', 'paid']).exists()
                if active_bookings:
                    messages.error(request, f"Cannot delete room {room.room_number}. It has active bookings.")
                else:
                    room_name = str(room)
                    # Get affected students before deleting
                    expired_bookings = Booking.objects.filter(room=room, status='expired')
                    if expired_bookings.exists():
                        from .utils import send_notification
                        for booking in expired_bookings:
                            subject = "Room Deleted by Admin"
                            message = (
                                f"Hello {booking.student.user.get_full_name()},\n\n"
                                f"Note: Room {room_name} that you previously booked has been removed from the system by the administration.\n\n"
                                f"This does not affect any active bookings or current students.\n\n"
                                f"Thank you,\nANU Hostel Management"
                            )
                            send_notification(booking.student, subject, message)
                    
                    room.delete()
                    messages.success(request, f"Room {room_name} deleted successfully.")
            except Room.DoesNotExist:
                messages.error(request, "Room not found.")
        
        elif action == 'add_hostel':
            name = request.POST.get('name')
            gender = request.POST.get('gender')
            room_type = request.POST.get('type')
            description = request.POST.get('description', '')
            
            if Hostel.objects.filter(name=name).exists():
                messages.error(request, f"Hostel {name} already exists.")
            else:
                Hostel.objects.create(
                    name=name,
                    gender=gender,
                    type=room_type,
                    description=description
                )
                messages.success(request, f"Hostel {name} added successfully.")
        
        elif action == 'edit_hostel':
            hostel_id = request.POST.get('hostel_id')
            name = request.POST.get('name')
            gender = request.POST.get('gender')
            room_type = request.POST.get('type')
            description = request.POST.get('description', '')
            
            try:
                hostel = Hostel.objects.get(id=hostel_id)
                if name != hostel.name and Hostel.objects.filter(name=name).exists():
                    messages.error(request, f"Hostel {name} already exists.")
                else:
                    old_name = hostel.name
                    hostel.name = name
                    hostel.gender = gender
                    hostel.type = room_type
                    hostel.description = description
                    hostel.save()
                    
                    # Notify students with bookings in this hostel about changes
                    active_bookings = Booking.objects.filter(
                        room__hostel=hostel, 
                        status__in=['prebooked', 'paid']
                    ).select_related('student__user', 'room')
                    
                    if active_bookings.exists():
                        from .utils import send_notification
                        changes = []
                        if old_name != name:
                            changes.append(f"Hostel name changed from '{old_name}' to '{name}'")
                        changes.append(f"Hostel details updated")
                        
                        for booking in active_bookings:
                            subject = "Hostel Information Updated by Admin"
                            message = (
                                f"Hello {booking.student.user.get_full_name()},\n\n"
                                f"Your hostel ({name}) has been updated by the administration.\n\n"
                                f"Changes:\n" + "\n".join(f"• {change}" for change in changes) + "\n\n"
                                f"Updated Description: {description or 'No description'}\n\n"
                                f"Your booking and room assignment remain unchanged.\n\n"
                                f"Thank you,\nANU Hostel Management"
                            )
                            send_notification(booking.student, subject, message)
                    
                    messages.success(request, f"Hostel {name} updated successfully.")
            except Hostel.DoesNotExist:
                messages.error(request, "Hostel not found.")
        
        elif action == 'delete_hostel':
            hostel_id = request.POST.get('hostel_id')
            try:
                hostel = Hostel.objects.get(id=hostel_id)
                if hostel.rooms.exists():
                    messages.error(request, f"Cannot delete hostel {hostel.name}. It has rooms assigned.")
                else:
                    hostel_name = hostel.name
                    hostel.delete()
                    messages.success(request, f"Hostel {hostel_name} deleted successfully.")
            except Hostel.DoesNotExist:
                messages.error(request, "Hostel not found.")
        
        return redirect('manage_rooms')
    
    context = {
        'hostels': hostels,
        'rooms': rooms,
    }
    return render(request, 'manage_rooms.html', context)


# -----------------------------
# ADMIN USER MANAGEMENT
# -----------------------------
@login_required
def manage_admins(request):
    if not request.user.is_staff:
        return redirect('student_dashboard')
    
    admins = User.objects.filter(is_staff=True).order_by('username')
    students = Student.objects.select_related('user').all().order_by('user__username')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_admin':
            username = request.POST.get('username')
            password = request.POST.get('password')
            email = request.POST.get('email', '')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            
            if User.objects.filter(username=username).exists():
                messages.error(request, f"Username {username} already exists.")
            else:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=True,
                    is_superuser=False
                )
                
                # Send notification to new admin if email provided
                if email:
                    try:
                        from django.core.mail import send_mail
                        send_mail(
                            'Admin Access Granted - ANU Hostel System',
                            f'Hello {first_name or username},\n\n'
                            f'You have been granted admin access to the ANU Hostel Prebooking Management System.\n\n'
                            f'Username: {username}\n'
                            f'You can now log in and access the admin dashboard.\n\n'
                            f'Thank you,\nANU Hostel Management',
                            'briankariuki386@gmail.com',
                            [email],
                            fail_silently=False,
                        )
                    except Exception:
                        pass  # Email notification optional
                
                messages.success(request, f"Admin {username} created successfully.")
        
        elif action == 'revoke_admin':
            user_id = request.POST.get('user_id')
            try:
                user = User.objects.get(id=user_id, is_staff=True)
                if user.id == request.user.id:
                    messages.error(request, "You cannot revoke your own admin access.")
                else:
                    username = user.username
                    email = user.email
                    user.is_staff = False
                    user.is_superuser = False
                    user.save()
                    
                    # Send notification to revoked admin if email provided
                    if email:
                        try:
                            from django.core.mail import send_mail
                            send_mail(
                                'Admin Access Revoked - ANU Hostel System',
                                f'Hello {user.get_full_name() or username},\n\n'
                                f'Your admin access to the ANU Hostel Prebooking Management System has been revoked.\n\n'
                                f'You can still access the system as a regular user if you have a student account.\n\n'
                                f'Thank you,\nANU Hostel Management',
                                'briankariuki386@gmail.com',
                                [email],
                                fail_silently=False,
                            )
                        except Exception:
                            pass  # Email notification optional
                    
                    messages.success(request, f"Admin access revoked for {username}.")
            except User.DoesNotExist:
                messages.error(request, "User not found.")
        
        elif action == 'promote_student':
            student_id = request.POST.get('student_id')
            try:
                student = Student.objects.get(id=student_id)
                user = student.user
                user.is_staff = True
                user.save()
                
                # Notify student about promotion
                from .utils import send_notification
                subject = "Promoted to Admin - ANU Hostel System"
                message = (
                    f"Hello {user.get_full_name() or user.username},\n\n"
                    f"Congratulations! You have been promoted to admin status in the ANU Hostel Prebooking Management System.\n\n"
                    f"You now have access to:\n"
                    f"• Admin Dashboard\n"
                    f"• Manage Bookings\n"
                    f"• Room Management\n"
                    f"• Admin User Management\n"
                    f"• Finance Dashboard\n\n"
                    f"Please log out and log back in to access admin features.\n\n"
                    f"Thank you,\nANU Hostel Management"
                )
                send_notification(student, subject, message)
                
                messages.success(request, f"{user.username} promoted to admin.")
            except Student.DoesNotExist:
                messages.error(request, "Student not found.")
        
        return redirect('manage_admins')
    
    context = {
        'admins': admins,
        'students': students,
    }
    return render(request, 'manage_admins.html', context)