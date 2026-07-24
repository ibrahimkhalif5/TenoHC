from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class DischargeSummary(TimeStampedModel):
    """Complete discharge summary for an admitted patient."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        FINALIZED = "FINALIZED", "Finalized"

    admission = models.OneToOneField(
        "admission.Admission",
        on_delete=models.CASCADE,
        related_name="discharge_summary",
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT,
    )

    # Section C - Clinical Information
    primary_diagnosis = models.TextField(blank=True, default="")
    secondary_diagnosis = models.TextField(blank=True, default="")
    reason_for_admission = models.TextField(blank=True, default="")
    history_of_present_illness = models.TextField(blank=True, default="")
    clinical_findings = models.TextField(blank=True, default="")
    investigations_performed = models.TextField(blank=True, default="")
    procedures_done = models.TextField(blank=True, default="")
    treatment_given = models.TextField(blank=True, default="")
    patient_progress = models.TextField(blank=True, default="")
    condition_on_discharge = models.TextField(blank=True, default="")

    # Section E - Follow-up Instructions
    doctor_advice = models.TextField(blank=True, default="")
    follow_up_date = models.DateField(null=True, blank=True)
    lifestyle_advice = models.TextField(blank=True, default="")
    diet_advice = models.TextField(blank=True, default="")
    activity_restrictions = models.TextField(blank=True, default="")
    warning_signs = models.TextField(blank=True, default="")

    # Section F - Doctor Information
    doctor_signature = models.ImageField(
        upload_to="signatures/", blank=True, null=True,
    )

    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discharge_summaries_created",
    )
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discharge_summaries_finalized",
    )
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Discharge Summary"
        verbose_name_plural = "Discharge Summaries"

    def __str__(self):
        return (
            f"Discharge Summary - {self.admission.patient.full_name} "
            f"({self.get_status_display()})"
        )

    @property
    def length_of_stay(self):
        admission = self.admission
        if admission.discharge_date:
            delta = admission.discharge_date - admission.admission_date
            return max(delta.days, 1)
        from datetime import date
        delta = date.today() - admission.admission_date
        return max(delta.days, 0)

    @property
    def is_finalized(self):
        return self.status == self.Status.FINALIZED

    def can_finalize(self):
        errors = []
        if not self.primary_diagnosis.strip():
            errors.append("Primary Diagnosis is required.")
        if not self.treatment_given.strip():
            errors.append("Treatment Given is required.")
        if not self.condition_on_discharge.strip():
            errors.append("Condition on Discharge is required.")
        if not self.discharge_medications.exists() and not self.doctor_advice.strip():
            errors.append(
                "At least one Discharge Medication or Doctor Advice is required."
            )
        return errors


class DischargeMedication(TimeStampedModel):
    """Medication prescribed at discharge."""

    discharge_summary = models.ForeignKey(
        DischargeSummary,
        on_delete=models.CASCADE,
        related_name="discharge_medications",
    )
    medicine_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, blank=True, default="")
    frequency = models.CharField(max_length=100, blank=True, default="")
    duration = models.CharField(max_length=100, blank=True, default="")
    instructions = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Discharge Medication"
        verbose_name_plural = "Discharge Medications"

    def __str__(self):
        return f"{self.medicine_name} - {self.dosage}"
