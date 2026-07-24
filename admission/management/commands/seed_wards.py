"""
Seed the database with wards, rooms, and beds.
"""
from django.core.management.base import BaseCommand
from admission.models import Ward, Room, Bed


class Command(BaseCommand):
    help = "Seed wards, rooms, and beds"

    def handle(self, *args, **options):
        wards_data = [
            ("General Ward", "GENERAL", "Standard ward for general patients", 5000),
            ("Executive Ward", "EXECUTIVE", "Premium ward with private rooms", 15000),
            ("VIP Ward", "VIP", "VIP ward with luxury amenities", 25000),
        ]

        rooms_data = {
            "General Ward": [
                ("G-101", "SHARED", 4),
                ("G-102", "SHARED", 4),
                ("G-103", "DOUBLE", 2),
            ],
            "Executive Ward": [
                ("E-201", "SINGLE", 1),
                ("E-202", "SINGLE", 1),
                ("E-203", "DOUBLE", 2),
            ],
            "VIP Ward": [
                ("V-301", "SINGLE", 1),
                ("V-302", "SINGLE", 1),
                ("V-303", "DOUBLE", 2),
            ],
        }

        ward_count = 0
        room_count = 0
        bed_count = 0

        for name, wtype, desc, price in wards_data:
            ward, created = Ward.objects.get_or_create(
                name=name,
                defaults={"ward_type": wtype, "description": desc, "price_per_night": price},
            )
            if created:
                ward_count += 1
                self.stdout.write(f"  + Ward: {name}")

            for room_num, rtype, capacity in rooms_data[name]:
                room, rc = Room.objects.get_or_create(
                    ward=ward, room_number=room_num,
                    defaults={"room_type": rtype, "capacity": capacity},
                )
                if rc:
                    room_count += 1
                    self.stdout.write(f"    + Room: {room_num}")

                # Create beds for the room
                for i in range(1, capacity + 1):
                    bed, bc = Bed.objects.get_or_create(
                        room=room, bed_number=f"{room_num}-B{i}",
                    )
                    if bc:
                        bed_count += 1
                        self.stdout.write(f"      + Bed: {room_num}-B{i}")

        self.stdout.write(self.style.SUCCESS(
            f"\nSeeded: {ward_count} wards, {room_count} rooms, {bed_count} beds "
            f"(Total: {Ward.objects.count()} wards, {Room.objects.count()} rooms, {Bed.objects.count()} beds)"
        ))
