from django.core.mail import send_mail
from twilio.rest import Client
import os

def send_notification(student, subject, message):
    """Send both in-system notification, email, and SMS via Twilio."""
    from .models import Notification  # Local import to prevent circular dependency

    # Save in-app notification
    note = Notification.objects.create(student=student, message=message)

    # Email notification
    if student.user.email:
        try:
            send_mail(
                subject,
                message,
                'briankariuki386@gmail.com',  # or your noreply email
                [student.user.email],
                fail_silently=False,
            )
            note.email_status = "Sent"
        except Exception as e:
            note.email_status = f"Failed ({str(e)[:50]})"
    else:
        note.email_status = "No Email"

    # SMS notification
    try:
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        twilio_number = os.getenv('TWILIO_PHONE_NUMBER')

        if account_sid and auth_token and twilio_number and student.phone:
            client = Client(account_sid, auth_token)
            formatted_phone = student.phone if student.phone.startswith('+') else f'+254{student.phone[-9:]}'
            client.messages.create(
                body=message,
                from_=twilio_number,
                to=formatted_phone
            )
            note.sms_status = "Sent"
        else:
            note.sms_status = "No Phone"
    except Exception as e:
        note.sms_status = f"Failed ({str(e)[:50]})"

    note.save()
