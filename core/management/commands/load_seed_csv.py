"""
Load all seed data from CSV files in seed_data/ directory.
Usage: python manage.py load_seed_csv
"""
import csv
import os
import sys
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Load seed data from CSV files in seed_data/ directory"

    def _find_seed_dir(self):
        candidates = []

        # Frozen exe: check _MEIPASS
        if getattr(sys, 'frozen', False):
            candidates.append(os.path.join(sys._MEIPASS, 'seed_data'))

        # Environment variable from launcher
        bundle = os.environ.get('TENOHMS_BUNDLE_DIR')
        if bundle:
            candidates.append(os.path.join(bundle, 'seed_data'))

        # settings.BASE_DIR
        base = getattr(settings, 'BASE_DIR', None)
        if base:
            candidates.append(os.path.join(str(base), 'seed_data'))

        # Current working directory
        candidates.append(os.path.join(os.getcwd(), 'seed_data'))

        # Script location fallback
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'seed_data'))

        for path in candidates:
            path = os.path.normpath(path)
            if os.path.isdir(path):
                return path
        return None

    def handle(self, *args, **options):
        seed_dir = self._find_seed_dir()
        if not seed_dir:
            self.stdout.write(self.style.ERROR("seed_data directory not found"))
            return

        self.stdout.write(f"Loading seed data from: {seed_dir}")

        self._load_categories(seed_dir)
        self._load_suppliers(seed_dir)
        self._load_medicines(seed_dir)
        self._load_lab_tests(seed_dir)
        self._load_radiology(seed_dir)
        self._load_wards(seed_dir)
        self._load_lab_templates(seed_dir)

        self.stdout.write(self.style.SUCCESS("\nAll seed data loaded successfully!"))

    def _read_csv(self, seed_dir, filename):
        path = os.path.join(seed_dir, filename)
        if not os.path.isfile(path):
            self.stdout.write(self.style.WARNING(f"  {filename} not found, skipping"))
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    def _load_categories(self, seed_dir):
        from inventory.models import MedicineCategory
        rows = self._read_csv(seed_dir, 'medicine_categories.csv')
        count = 0
        for row in rows:
            _, created = MedicineCategory.objects.get_or_create(
                name=row['name'], defaults={'description': row['description']}
            )
            if created:
                count += 1
        self.stdout.write(f"  Categories: {count} created (total: {MedicineCategory.objects.count()})")

    def _load_suppliers(self, seed_dir):
        from inventory.models import Supplier
        rows = self._read_csv(seed_dir, 'suppliers.csv')
        count = 0
        for row in rows:
            _, created = Supplier.objects.get_or_create(
                name=row['name'],
                defaults={
                    'contact_person': row['contact_person'],
                    'phone': row['phone'],
                    'email': row['email'],
                    'address': row['address'],
                }
            )
            if created:
                count += 1
        self.stdout.write(f"  Suppliers: {count} created (total: {Supplier.objects.count()})")

    def _load_medicines(self, seed_dir):
        from inventory.models import Medicine, MedicineCategory
        rows = self._read_csv(seed_dir, 'medicines.csv')
        count = 0
        for row in rows:
            cat_name = row.get('category', '')
            category = MedicineCategory.objects.filter(name=cat_name).first()
            _, created = Medicine.objects.get_or_create(
                name=row['name'],
                defaults={
                    'generic_name': row['generic_name'],
                    'category': category,
                    'dosage_form': row['dosage_form'],
                    'strength': row['strength'],
                    'unit': row['unit'],
                    'selling_price': int(row['selling_price']),
                    'cost_price': int(row['cost_price']),
                    'minimum_stock': int(row['minimum_stock']),
                    'reorder_level': int(row['reorder_level']),
                }
            )
            if created:
                count += 1
        self.stdout.write(f"  Medicines: {count} created (total: {Medicine.objects.count()})")

    def _load_lab_tests(self, seed_dir):
        from laboratory.models import LabTest
        rows = self._read_csv(seed_dir, 'lab_tests.csv')
        count = 0
        for row in rows:
            _, created = LabTest.objects.update_or_create(
                name=row['name'],
                defaults={
                    'category': row['category'],
                    'price': int(row['price']),
                    'normal_range': row.get('normal_range', ''),
                    'unit': row.get('unit', ''),
                    'turnaround_time': row.get('turnaround_time', ''),
                    'is_active': True,
                }
            )
            if created:
                count += 1
        self.stdout.write(f"  Lab tests: {count} created (total: {LabTest.objects.count()})")

    def _load_radiology(self, seed_dir):
        from radiology.models import RadiologyService
        rows = self._read_csv(seed_dir, 'radiology_services.csv')
        count = 0
        for row in rows:
            _, created = RadiologyService.objects.get_or_create(
                name=row['name'],
                defaults={
                    'service_type': row['service_type'],
                    'body_part': row['body_part'],
                    'description': row['description'],
                    'price': int(row['price']),
                }
            )
            if created:
                count += 1
        self.stdout.write(f"  Radiology services: {count} created (total: {RadiologyService.objects.count()})")

    def _load_wards(self, seed_dir):
        from admission.models import Ward, Room, Bed
        rows = self._read_csv(seed_dir, 'wards.csv')
        ward_count = 0
        room_count = 0
        bed_count = 0

        rooms_data = {
            "General Ward": [("G-101", "SHARED", 4), ("G-102", "SHARED", 4), ("G-103", "DOUBLE", 2)],
            "Executive Ward": [("E-201", "SINGLE", 1), ("E-202", "SINGLE", 1), ("E-203", "DOUBLE", 2)],
            "VIP Ward": [("V-301", "SINGLE", 1), ("V-302", "SINGLE", 1), ("V-303", "DOUBLE", 2)],
        }

        for row in rows:
            ward, created = Ward.objects.get_or_create(
                name=row['name'],
                defaults={
                    'ward_type': row['ward_type'],
                    'description': row['description'],
                    'price_per_night': int(row['price_per_night']),
                }
            )
            if created:
                ward_count += 1

            for room_num, rtype, capacity in rooms_data.get(row['name'], []):
                room, rc = Room.objects.get_or_create(
                    ward=ward, room_number=room_num,
                    defaults={'room_type': rtype, 'capacity': capacity}
                )
                if rc:
                    room_count += 1
                for i in range(1, capacity + 1):
                    bed, bc = Bed.objects.get_or_create(
                        room=room, bed_number=f"{room_num}-B{i}"
                    )
                    if bc:
                        bed_count += 1

        self.stdout.write(f"  Wards: {ward_count} created | Rooms: {room_count} | Beds: {bed_count}")

    def _load_lab_templates(self, seed_dir):
        from laboratory.models import LabTest, LabTestTemplate, LabTestParameter

        fbc_params = [
            {"name": "WBC", "unit": "x10⁹/L", "normal_range": "4.0 - 10.0", "normal_min": 4.0, "normal_max": 10.0},
            {"name": "LYMPH%", "unit": "%", "normal_range": "20 - 40", "normal_min": 20, "normal_max": 40},
            {"name": "LYMPH#", "unit": "x10⁹/L", "normal_range": "0.6 - 4.1", "normal_min": 0.6, "normal_max": 4.1},
            {"name": "GRAN#", "unit": "x10⁹/L", "normal_range": "2.0 - 7.8", "normal_min": 2.0, "normal_max": 7.8},
            {"name": "GRAN%", "unit": "%", "normal_range": "50 - 70", "normal_min": 50, "normal_max": 70},
            {"name": "HB", "unit": "g/dL", "normal_range": "11.5 - 18.0", "normal_min": 11.5, "normal_max": 18.0},
            {"name": "RBC", "unit": "x10¹²/L", "normal_range": "3.5 - 5.5", "normal_min": 3.5, "normal_max": 5.5},
            {"name": "HCT", "unit": "%", "normal_range": "37 - 54", "normal_min": 37, "normal_max": 54},
            {"name": "MCV", "unit": "fL", "normal_range": "80 - 100", "normal_min": 80, "normal_max": 100},
            {"name": "MCH", "unit": "pg", "normal_range": "27 - 34", "normal_min": 27, "normal_max": 34},
            {"name": "MCHC", "unit": "g/dL", "normal_range": "34.7 - 36", "normal_min": 34.7, "normal_max": 36},
            {"name": "RDW-CV", "unit": "%", "normal_range": "11 - 16", "normal_min": 11, "normal_max": 16},
            {"name": "RDW-SD", "unit": "fL", "normal_range": "35 - 56", "normal_min": 35, "normal_max": 56},
            {"name": "PLT", "unit": "x10⁹/L", "normal_range": "150 - 450", "normal_min": 150, "normal_max": 450},
            {"name": "PCT", "unit": "mL/L", "normal_range": "1.08 - 2.82", "normal_min": 1.08, "normal_max": 2.82},
            {"name": "MPV", "unit": "fL", "normal_range": "6.5 - 12", "normal_min": 6.5, "normal_max": 12},
            {"name": "PDW", "unit": "%", "normal_range": "0 - 17", "normal_min": 0, "normal_max": 17},
            {"name": "MID#", "unit": "x10⁹/L", "normal_range": "0.1 - 1.5", "normal_min": 0.1, "normal_max": 1.5},
        ]

        lab_test = LabTest.objects.filter(name__icontains="FBC").first()
        if not lab_test:
            lab_test = LabTest.objects.filter(name__icontains="Full Blood").first()
        if not lab_test:
            self.stdout.write(self.style.WARNING("  Lab templates: FBC test not found, skipping"))
            return

        template, created = LabTestTemplate.objects.get_or_create(
            lab_test=lab_test,
            defaults={"instructions": "Enter result values only. Auto-flagging enabled.", "is_active": True},
        )
        if created:
            for i, param in enumerate(fbc_params):
                LabTestParameter.objects.create(
                    template=template, name=param["name"], unit=param["unit"],
                    normal_range=param["normal_range"], normal_min=param["normal_min"],
                    normal_max=param["normal_max"], display_order=i,
                )
            self.stdout.write(f"  Lab template FBC: created with {len(fbc_params)} parameters")
        else:
            self.stdout.write(f"  Lab template FBC: already exists")
