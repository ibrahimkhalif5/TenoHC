from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class Visit(TimeStampedModel):
    """A patient visit/encounter."""

    class Status(models.TextChoices):
        WAITING_TRIAGE = "WAITING_TRIAGE", "Waiting for Triage"
        IN_TRIAGE = "IN_TRIAGE", "In Triage"
        WAITING_DOCTOR = "WAITING_DOCTOR", "Waiting for Doctor"
        IN_CONSULTATION = "IN_CONSULTATION", "In Consultation"
        WAITING_LAB = "WAITING_LAB", "Waiting for Lab"
        WAITING_XRAY = "WAITING_XRAY", "Waiting for X-Ray"
        WAITING_ULTRASOUND = "WAITING_ULTRASOUND", "Waiting for Ultrasound"
        WAITING_DOCTOR_REVIEW = "WAITING_DOCTOR_REVIEW", "Waiting for Doctor Review"
        WAITING_PHARMACY = "WAITING_PHARMACY", "Waiting for Pharmacy"
        ADMISSION_IN_PROGRESS = "ADMISSION_IN_PROGRESS", "Admission In Progress"
        DISCHARGED = "DISCHARGED", "Discharged"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="visits",
    )
    visit_number = models.CharField(max_length=20, unique=True, editable=False)
    visit_date = models.DateField(auto_now_add=True)
    status = models.CharField(
        max_length=35, choices=Status.choices, default=Status.WAITING_TRIAGE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.visit_number} - {self.patient.full_name} ({self.get_status_display()})"

    def get_stage_url(self):
        """Return the URL for the current stage of this visit's journey."""
        from django.urls import reverse
        status = self.status
        if status == self.Status.WAITING_TRIAGE:
            return reverse("triage:triage-list")
        elif status == self.Status.IN_TRIAGE:
            return reverse("triage:triage-assess", kwargs={"visit_id": self.pk})
        elif status == self.Status.WAITING_DOCTOR:
            return reverse("consultation:consultation-list")
        elif status == self.Status.IN_CONSULTATION:
            from consultation.models import Consultation
            cons = Consultation.objects.filter(visit=self, status="IN_PROGRESS").first()
            if cons:
                return reverse("consultation:conduct-consultation", kwargs={"consultation_id": cons.pk})
            return reverse("consultation:consultation-list")
        elif status == self.Status.WAITING_LAB:
            return reverse("laboratory:lab-detail", kwargs={"visit_id": self.pk})
        elif status in (self.Status.WAITING_XRAY, self.Status.WAITING_ULTRASOUND):
            return reverse("radiology:radiology-detail", kwargs={"visit_id": self.pk})
        elif status == self.Status.WAITING_DOCTOR_REVIEW:
            from consultation.models import Consultation
            cons = Consultation.objects.filter(visit=self).order_by("-started_at").first()
            if cons:
                return reverse("consultation:conduct-consultation", kwargs={"consultation_id": cons.pk})
            return reverse("consultation:consultation-list")
        elif status == self.Status.WAITING_PHARMACY:
            return reverse("pharmacy:pharmacy-dispense", kwargs={"visit_id": self.pk})
        elif status == self.Status.ADMISSION_IN_PROGRESS:
            return reverse("admission:admission-list")
        elif status == self.Status.DISCHARGED:
            return reverse("patients:patient-detail", kwargs={"pk": self.patient_id})
        elif status == self.Status.COMPLETED:
            return reverse("patients:patient-detail", kwargs={"pk": self.patient_id})
        return reverse("dashboard:index")


class TriageAssessment(TimeStampedModel):
    """Triage vitals capture."""
    visit = models.ForeignKey(
        Visit, on_delete=models.CASCADE, related_name="triage_assessments",
    )

    # Vitals
    temperature = models.DecimalField(max_digits=4, decimal_places=1, help_text="Celsius")
    weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="kg")
    height = models.DecimalField(max_digits=5, decimal_places=2, help_text="cm")
    blood_pressure_systolic = models.PositiveIntegerField(help_text="mmHg", null=True, blank=True)
    blood_pressure_diastolic = models.PositiveIntegerField(help_text="mmHg", null=True, blank=True)
    pulse = models.PositiveIntegerField(help_text="bpm")
    respiratory_rate = models.PositiveIntegerField(help_text="breaths/min")
    oxygen_saturation = models.DecimalField(max_digits=4, decimal_places=1, help_text="%")

    # Notes
    chief_complaint = models.TextField()
    nurse_notes = models.TextField(blank=True)

    # Audit
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    assessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-assessed_at"]

    def __str__(self):
        return f"Triage for {self.visit.visit_number} - {self.visit.patient.full_name}"


class VisitEvent(TimeStampedModel):
    """Audit trail of every workflow event for a visit."""
    visit = models.ForeignKey(
        Visit, on_delete=models.CASCADE, related_name="events",
    )
    event_type = models.CharField(max_length=50)
    description = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]
        verbose_name = "Visit Event"
        verbose_name_plural = "Visit Events"

    def __str__(self):
        return f"{self.visit.visit_number} - {self.event_type} ({self.timestamp:%H:%M})"
