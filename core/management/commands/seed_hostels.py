from django.core.management.base import BaseCommand
from core.models import Hostel, Room

class Command(BaseCommand):
    help = "Seeds hostel and room data for ANU Hostel System"

    def handle(self, *args, **options):
        # Clear existing data
        Room.objects.all().delete()
        Hostel.objects.all().delete()

        # Define hostel data based on requirements
        data = [
            # Male hostels - 60 rooms total (20 each)
            {
                "name": "Zanner",
                "gender": "Male",
                "rooms": [
                    {"type": "Type 1", "count": 2, "price": 28000, "description": "Ethernet ports, decent bed structure, TV, no bathroom"},
                    {"type": "Regular", "count": 18, "price": 24000, "description": "Standard room with beds and wardrobe"},
                ],
            },
            {
                "name": "Johnson",
                "gender": "Male",
                "rooms": [
                    {"type": "Regular", "count": 20, "price": 24000, "description": "Standard room with beds and wardrobe"},
                ],
            },
            {
                "name": "Cashman",
                "gender": "Male",
                "rooms": [
                    {"type": "Ensuite", "count": 1, "price": 28000, "description": "Bathroom, TV"},
                    {"type": "Regular", "count": 19, "price": 24000, "description": "Standard room with beds and wardrobe"},
                ],
            },
            # Female hostels - 60 rooms total
            {
                "name": "Crawford",
                "gender": "Female",
                "rooms": [
                    {"type": "Type 1", "count": 2, "price": 35000, "description": "Type 1 Ensuite - Private Bathroom + Toilet, TV, ethernet port, good bed structure"},
                    {"type": "Ensuite", "count": 5, "price": 28000, "description": "Ensuite with bathroom and TV"},
                    {"type": "Regular", "count": 53, "price": 24000, "description": "Standard room with beds and wardrobe"},
                ],
            },
        ]

        for hostel_data in data:
            # Create hostels for each room type
            for room_type_data in hostel_data["rooms"]:
                room_type = room_type_data["type"]
                hostel_name = f"{hostel_data['name']} {room_type}" if room_type != "Regular" else f"{hostel_data['name']}"
                
                # Special case: Crawford Type 1 should be "Crawford Type 1"
                if hostel_data["name"] == "Crawford" and room_type == "Type 1":
                    hostel_name = "Crawford Type 1"
                elif hostel_data["name"] == "Crawford" and room_type == "Regular":
                    hostel_name = "Crawford Regular"
                elif hostel_data["name"] == "Crawford" and room_type == "Ensuite":
                    hostel_name = "Crawford Ensuite"
                
                hostel = Hostel.objects.create(
                    name=hostel_name,
                    gender=hostel_data["gender"],
                    type=room_type,
                    description=room_type_data["description"],
                )

                # Create rooms for this hostel
                room_count = room_type_data["count"]
                price = room_type_data["price"]
                
                for i in range(1, room_count + 1):
                    Room.objects.create(
                        hostel=hostel,
                        room_number=f"{i:02d}",
                        capacity=2,
                        is_vacant=True,
                        price=price,
                    )

        self.stdout.write(self.style.SUCCESS("✅ Hostels and rooms successfully seeded!"))
        self.stdout.write(self.style.SUCCESS(f"   Created {Hostel.objects.count()} hostels"))
        self.stdout.write(self.style.SUCCESS(f"   Created {Room.objects.count()} rooms"))
