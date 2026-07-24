from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class Consultation(TimeStampedModel):
    """A doctor's consultation for a patient visit."""

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    visit = models.ForeignKey(
        "triage.Visit", on_delete=models.CASCADE, related_name="consultations",
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="consultations",
    )
    item = models.ForeignKey(
        "core.Item", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="consultations", help_text="Linked Item Master entry",
    )
    diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    treatment_plan = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS,
    )
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=50)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Consultation - {self.visit.visit_number} ({self.get_status_display()})"


class Prescription(TimeStampedModel):
    """A prescription line item from a consultation."""

    class DosageUnit(models.TextChoices):
        MG = "MG", "mg"
        ML = "ML", "ml"
        TABLET = "TABLET", "tablet(s)"
        CAPSULE = "CAPSULE", "capsule(s)"
        DROP = "DROP", "drop(s)"
        PUFF = "PUFF", "puff(s)"
        UNIT = "UNIT", "unit(s)"

    consultation = models.ForeignKey(
        Consultation, on_delete=models.CASCADE, related_name="prescriptions",
    )
    medicine = models.ForeignKey(
        "inventory.Medicine", on_delete=models.RESTRICT, related_name="prescriptions",
    )
    dosage = models.CharField(max_length=100, help_text="e.g., 500mg")
    dosage_unit = models.CharField(
        max_length=20, choices=DosageUnit.choices, default=DosageUnit.MG,
    )
    frequency = models.CharField(max_length=100, help_text="e.g., 3 times daily")
    duration_days = models.PositiveIntegerField(help_text="Number of days")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total quantity to dispense")
    route = models.CharField(max_length=100, blank=True, default="Oral")
    instructions = models.TextField(blank=True, help_text="Additional instructions")
    is_dispensed = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.medicine.name} - {self.dosage} {self.get_dosage_unit_display()}"
