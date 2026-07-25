"""
Seed the core.Item master catalogue with medicines, lab tests, and radiology services.
"""
import csv
import os
import sys
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed core.Item master catalogue from seed_data CSVs and inventory models"

    def _find_seed_dir(self):
        if getattr(sys, 'frozen', False):
            p = os.path.join(sys._MEIPASS, 'seed_data')
            if os.path.isdir(p):
                return p
        bundle = os.environ.get('TENOHMS_BUNDLE_DIR')
        if bundle:
            p = os.path.join(bundle, 'seed_data')
            if os.path.isdir(p):
                return p
        cwd = os.path.join(os.getcwd(), 'seed_data')
        if os.path.isdir(cwd):
            return cwd
        return None

    def _read_csv(self, seed_dir, filename):
        path = os.path.join(seed_dir, filename)
        if not os.path.isfile(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    def handle(self, *args, **options):
        from core.models import Item

        seed_dir = self._find_seed_dir()
        if not seed_dir:
            self.stdout.write(self.style.ERROR("seed_data directory not found"))
            return

        self.stdout.write(f"Seeding Item Master from: {seed_dir}")
        count = 0

        # Medicines
        for row in self._read_csv(seed_dir, 'medicines.csv'):
            _, created = Item.objects.get_or_create(
                name=row['name'],
                category=Item.Category.MEDICINE,
                defaults={
                    'unit_price': float(row['selling_price']),
                    'cost_price': float(row['cost_price']),
                    'unit_of_measure': row['unit'],
                    'department': Item.Department.PHARMACY,
                    'is_active': True,
                },
            )
            if created:
                count += 1

        # Lab Tests
        for row in self._read_csv(seed_dir, 'lab_tests.csv'):
            _, created = Item.objects.get_or_create(
                name=row['name'],
                category=Item.Category.LAB_TEST,
                defaults={
                    'unit_price': float(row['price']),
                    'unit_of_measure': 'Test',
                    'normal_range': row.get('normal_range', ''),
                    'unit': row.get('unit', ''),
                    'department': Item.Department.LABORATORY,
                    'is_active': True,
                },
            )
            if created:
                count += 1

        # Radiology Services
        for row in self._read_csv(seed_dir, 'radiology_services.csv'):
            cat = Item.Category.RADIOLOGY
            if row['service_type'] == 'ULTRASOUND':
                cat = Item.Category.ULTRASOUND
            _, created = Item.objects.get_or_create(
                name=row['name'],
                category=cat,
                defaults={
                    'unit_price': float(row['price']),
                    'unit_of_measure': 'Scan',
                    'description': row.get('description', ''),
                    'department': Item.Department.RADIOLOGY,
                    'is_active': True,
                },
            )
            if created:
                count += 1

        total = Item.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Item Master: {count} created (total: {total})"))
