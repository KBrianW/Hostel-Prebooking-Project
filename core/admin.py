from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Student, Hostel, Room, Booking, Payment, Notification

# -----------------------------
# INLINE ADMIN FOR STUDENT PROFILE LINKED TO USER
# -----------------------------
class StudentInline(admin.StackedInline):
    model = Student
    can_delete = False
    verbose_name_plural = 'Student Profile'
    fk_name = 'user'


class CustomUserAdmin(UserAdmin):
    inlines = (StudentInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


# Unregister default User admin, then register custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# -----------------------------
# HOSTEL ADMIN
# -----------------------------
@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'description')
    search_fields = ('name',)
    list_filter = ('type',)

# -----------------------------
# ROOM ADMIN
# -----------------------------
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'hostel', 'capacity', 'is_vacant')
    list_filter = ('hostel', 'is_vacant')
    search_fields = ('room_number', 'hostel__name')

# -----------------------------
# BOOKING ADMIN
# -----------------------------
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('student', 'room', 'status', 'date_booked', 'expiry_date')
    list_filter = ('status', 'date_booked')
    search_fields = ('student__reg_no', 'room__room_number')

# -----------------------------
# PAYMENT ADMIN
# -----------------------------
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'payment_type', 'verified', 'date_paid')
    list_filter = ('verified', 'payment_type')
    search_fields = ('booking__student__reg_no',)
    list_editable = ('verified',)

# -----------------------------
# NOTIFICATION ADMIN
# -----------------------------
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'student', 
        'short_message', 
        'date_sent', 
        'email_status', 
        'sms_status', 
        'is_read'
    )
    list_filter = ('email_status', 'sms_status', 'is_read', 'date_sent')
    search_fields = ('student__reg_no', 'message')

    def short_message(self, obj):
        """Show a shortened preview of the message."""
        return (obj.message[:60] + "...") if len(obj.message) > 60 else obj.message
    short_message.short_description = "Message"
