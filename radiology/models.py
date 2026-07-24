from django.db import models
from core.models import TimeStampedModel, IsActiveModel


class RadiologyService(IsActiveModel):
    """Master data: available radiology/imaging service."""

    class ServiceType(models.TextChoices):
        XRAY = "XRAY", "X-Ray"
        ULTRASOUND = "ULTRASOUND", "Ultrasound"
        MRI = "MRI", "MRI"
        CT_SCAN = "CT_SCAN", "CT Scan"
        OTHER = "OTHER", "Other"

    item = models.ForeignKey(
        "core.Item", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="radiology_services", help_text="Linked Item Master entry",
    )
    name = models.CharField(max_length=200)
    service_type = models.CharField(max_length=20, choices=ServiceType.choices)
    body_part = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["service_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_service_type_display()})"


class RadiologyRequest(TimeStampedModel):
    """A radiology/imaging request for a patient visit."""

    class Priority(models.TextChoices):
        ROUTINE = "ROUTINE", "Routine"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        FINAL = "FINAL", "Final"

    visit = models.ForeignKey(
        "triage.Visit", on_delete=models.CASCADE, related_name="radiology_requests",
    )
    radiology_service = models.ForeignKey(
        RadiologyService, on_delete=models.RESTRICT, related_name="requests",
    )
    clinical_indication = models.TextField(blank=True, help_text="Why this imaging is requested")
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.ROUTINE,
    )
    findings = models.TextField(blank=True)
    impression = models.TextField(blank=True)
    image = models.ImageField(upload_to="radiology/images/", blank=True, null=True)
    result_status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT,
    )
    is_completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="radiology_requests_created",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.radiology_service.name} - {self.visit.visit_number}"
