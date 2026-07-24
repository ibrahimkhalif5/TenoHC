from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class PharmacyDispense(TimeStampedModel):
    """Record of a medication dispensed to a patient."""

    visit = models.ForeignKey(
        "triage.Visit", on_delete=models.CASCADE, related_name="pharmacy_dispenses",
    )
    prescription = models.ForeignKey(
        "consultation.Prescription", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="pharmacy_dispenses",
    )
    medicine = models.ForeignKey(
        "inventory.Medicine", on_delete=models.RESTRICT, related_name="pharmacy_dispenses",
    )
    quantity_dispensed = models.DecimalField(max_digits=10, decimal_places=2)
    batch_number = models.CharField(max_length=100, blank=True)
    charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    dispensed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="dispensations",
    )
    dispensed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-dispensed_at"]

    def __str__(self):
        return f"{self.medicine.name} x{self.quantity_dispensed} - {self.visit.visit_number}"
