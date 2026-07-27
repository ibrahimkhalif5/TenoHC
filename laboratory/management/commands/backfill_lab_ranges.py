"""
Backfill LabTest.normal_range from linked Item.normal_range
for all lab tests that have an empty normal_range.
"""
from django.core.management.base import BaseCommand

from laboratory.models import LabTest


class Command(BaseCommand):
    help = "Backfill empty LabTest.normal_range from linked Item.normal_range"

    def handle(self, *args, **options):
        updated = 0
        for lt in LabTest.objects.filter(normal_range="").select_related("item"):
            if lt.item and lt.item.normal_range:
                lt.normal_range = lt.item.normal_range
                if not lt.unit and lt.item.unit:
                    lt.unit = lt.item.unit
                lt.save(update_fields=["normal_range", "unit", "updated_at"])
                self.stdout.write(f"  Updated: {lt.name} -> {lt.normal_range}")
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Backfilled {updated} lab test(s) with reference ranges."))
