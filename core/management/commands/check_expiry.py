from django.core.management.base import BaseCommand
from core.tasks import check_payment_expiry

class Command(BaseCommand):
    help = "Checks for expired hostel pre-bookings and sends notifications"

    def handle(self, *args, **options):
        check_payment_expiry()
        self.stdout.write(self.style.SUCCESS("Checked and updated expired bookings successfully!"))
