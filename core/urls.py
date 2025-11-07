from django.urls import path
from . import views

urlpatterns = [
    # Login routes
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboards
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('student-profile/', views.student_profile, name='student_profile'),
    path('admin-profile/', views.admin_profile, name='admin_profile'),
    path('roommates/', views.view_roommates, name='view_roommates'),
    path('room/<int:room_id>/', views.view_room_details, name='view_room_details'),
    path('available-rooms/', views.available_rooms, name='available_rooms'),
    path('finance-dashboard/', views.finance_dashboard, name='finance_dashboard'),
    path('notification/read/<int:notification_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('notifications/read_all/', views.mark_all_notifications_as_read, name='mark_all_notifications_as_read'),
    path('notifications/', views.notifications_page, name='notifications_page'),
    path('fetch-notifications/', views.fetch_notifications, name='fetch_notifications'),
    #Admin routes
    path('manage-bookings/', views.manage_bookings, name='manage_bookings'),
    path('admin-notifications/', views.admin_notifications_page, name='admin_notifications_page'),
    path('manage-rooms/', views.manage_rooms, name='manage_rooms'),
    path('manage-admins/', views.manage_admins, name='manage_admins'),


]
