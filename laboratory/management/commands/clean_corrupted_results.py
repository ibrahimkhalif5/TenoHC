"""
Clean up corrupted LabTestResultValue records.

When the structured result template had a bug, each input field rendered
the entire result_values dict as its value. On form submit, every
parameter received the full dict string instead of its individual value.

This command detects and deletes those corrupted records so results can
be re-entered correctly.
"""
from django.core.management.base import BaseCommand

from laboratory.models import LabTestResultValue


class Command(BaseCommand):
    help = "Delete corrupted LabTestResultValue records where value is a dict string"

    def handle(self, *args, **options):
        corrupted = LabTestResultValue.objects.filter(value__startswith="{")
        count = corrupted.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No corrupted records found."))
            return

        corrupted.delete()
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {count} corrupted LabTestResultValue record(s).")
        )
