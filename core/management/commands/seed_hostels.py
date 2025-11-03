from django.core.management.base import BaseCommand
from core.models import Hostel, Room

class Command(BaseCommand):
    help = "Seeds hostel and room data for ANU Hostel System"

    def handle(self, *args, **options):
        data = [
            # Male hostels
            {
                "name": "Zanner",
                "type": "Male",
                "ensuite": 2,
                "regular": 18,
                "ensuite_price": 28000,
                "regular_price": 24000,
                "ensuite_desc": "Good bed structure, TV, and ethernet ports.",
                "regular_desc": "Standard room for two students.",
            },
            {
                "name": "Cahsman",
                "type": "Male",
                "ensuite": 1,
                "regular": 19,
                "ensuite_price": 28000,
                "regular_price": 24000,
                "ensuite_desc": "Bathroom and toilet included, ethernet ports.",
                "regular_desc": "Standard room for two students.",
            },
            {
                "name": "Johnson",
                "type": "Male",
                "ensuite": 0,
                "regular": 20,
                "regular_price": 24000,
                "regular_desc": "Standard room for two students.",
            },
            # Female hostels
            {
                "name": "Crawford Type 1",
                "type": "Female",
                "ensuite": 20,
                "regular": 0,
                "ensuite_price": 35000,
                "ensuite_desc": "Premium ensuite with TV, private bathroom, ethernet ports.",
            },
            {
                "name": "Crawford Ensuite",
                "type": "Female",
                "ensuite": 20,
                "regular": 0,
                "ensuite_price": 28000,
                "ensuite_desc": "Ensuite with bathroom and toilet, ethernet ports.",
            },
            {
                "name": "Crawford Regular",
                "type": "Female",
                "ensuite": 0,
                "regular": 20,
                "regular_price": 24000,
                "regular_desc": "Standard regular room for two students.",
            },
        ]

        Room.objects.all().delete()
        Hostel.objects.all().delete()

        for hostel_data in data:
            hostel = Hostel.objects.create(
                name=hostel_data["name"],
                type=hostel_data["type"],
                description=hostel_data.get("ensuite_desc", hostel_data.get("regular_desc", "")),
            )

            # Create ensuite rooms
            for i in range(1, hostel_data.get("ensuite", 0) + 1):
                Room.objects.create(
                    hostel=hostel,
                    room_number=f"E{i:02}",
                    capacity=2,
                    is_vacant=True,
                )

            # Create regular rooms
            for i in range(1, hostel_data.get("regular", 0) + 1):
                Room.objects.create(
                    hostel=hostel,
                    room_number=f"R{i:02}",
                    capacity=2,
                    is_vacant=True,
                )

        self.stdout.write(self.style.SUCCESS("✅ Hostels and rooms successfully seeded!"))
