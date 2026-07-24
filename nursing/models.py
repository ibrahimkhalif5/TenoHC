from datetime import date
from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class NursingNote(TimeStampedModel):
    """Nursing note for an admitted patient."""

    admission = models.ForeignKey(
        "admission.Admission", on_delete=models.CASCADE, related_name="nursing_notes",
    )
    note = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note for {self.admission.patient.full_name} - {self.created_at:%d %b %H:%M}"


class DailyVitals(TimeStampedModel):
    """Daily vitals recorded for an admitted patient."""

    admission = models.ForeignKey(
        "admission.Admission", on_delete=models.CASCADE, related_name="daily_vitals",
    )
    record_date = models.DateField(default=date.today)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, help_text="°C")
    blood_pressure_systolic = models.PositiveIntegerField(help_text="mmHg")
    blood_pressure_diastolic = models.PositiveIntegerField(help_text="mmHg")
    pulse = models.PositiveIntegerField(help_text="bpm")
    respiratory_rate = models.PositiveIntegerField(help_text="breaths/min")
    oxygen_saturation = models.DecimalField(max_digits=4, decimal_places=1, help_text="%")
    weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="kg", null=True, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        ordering = ["-record_date", "-created_at"]
        verbose_name_plural = "daily vitals"

    def __str__(self):
        return f"Vitals for {self.admission.patient.full_name} - {self.record_date}"


class Treatment(TimeStampedModel):
    """Treatment/medication given to an admitted patient."""

    admission = models.ForeignKey(
        "admission.Admission", on_delete=models.CASCADE, related_name="treatments",
    )
    treatment = models.CharField(max_length=500, help_text="Description of treatment/procedure")
    medication = models.CharField(max_length=200, blank=True, help_text="Medication name if applicable")
    dosage = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=100, blank=True, help_text="e.g. Once, Twice daily, Every 8 hours")
    notes = models.TextField(blank=True)
    given_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.treatment} - {self.admission.patient.full_name}"
