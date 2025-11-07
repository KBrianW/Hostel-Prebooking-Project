from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Student, Hostel, Room, Booking, Payment, Notification, FinanceTransaction

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
    list_display = ('name', 'gender', 'type', 'description')
    search_fields = ('name',)
    list_filter = ('gender', 'type',)

# -----------------------------
# ROOM ADMIN
# -----------------------------
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'hostel', 'price', 'capacity', 'is_vacant', 'get_occupied_count')
    list_filter = ('hostel', 'is_vacant')
    search_fields = ('room_number', 'hostel__name')
    list_editable = ('price', 'is_vacant')
    
    def get_occupied_count(self, obj):
        return obj.get_occupied_count()
    get_occupied_count.short_description = 'Occupied'

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

# -----------------------------
# FINANCE TRANSACTION ADMIN
# -----------------------------
@admin.register(FinanceTransaction)
class FinanceTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'date_created', 
        'transaction_type', 
        'student', 
        'amount', 
        'status',
        'booking'
    )
    list_filter = ('transaction_type', 'status', 'date_created')
    search_fields = ('student__reg_no', 'student__user__first_name', 'student__user__last_name', 'description')
    readonly_fields = ('date_created', 'date_completed')
    list_editable = ('status',)
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('transaction_type', 'amount', 'status', 'description')
        }),
        ('Related Information', {
            'fields': ('student', 'booking')
        }),
        ('Timestamps', {
            'fields': ('date_created', 'date_completed')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('student__user', 'booking__room')
