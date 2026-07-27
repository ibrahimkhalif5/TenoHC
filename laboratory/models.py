from django.db import models
from core.models import TimeStampedModel, IsActiveModel


class LabTest(IsActiveModel):
    """Master data: available laboratory test."""

    class Category(models.TextChoices):
        HAEMATOLOGY = "HAEMATOLOGY", "Haematology"
        CHEMISTRY = "CHEMISTRY", "Chemistry"
        MICROBIOLOGY = "MICROBIOLOGY", "Microbiology"
        IMMUNOLOGY = "IMMUNOLOGY", "Immunology"
        PATHOLOGY = "PATHOLOGY", "Pathology"
        OTHER = "OTHER", "Other"

    item = models.ForeignKey(
        "core.Item", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lab_tests", help_text="Linked Item Master entry",
    )
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=Category.choices)
    description = models.TextField(blank=True)
    normal_range = models.CharField(max_length=200, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    turnaround_time = models.CharField(max_length=100, blank=True, help_text="e.g., 24 hours")

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    @property
    def reference_range(self):
        """Return normal_range, falling back to linked Item's normal_range."""
        if self.normal_range:
            return self.normal_range
        if self.item and self.item.normal_range:
            return self.item.normal_range
        return ""


class LabRequest(TimeStampedModel):
    """A laboratory test request for a patient visit."""

    class Priority(models.TextChoices):
        ROUTINE = "ROUTINE", "Routine"
        URGENT = "URGENT", "Urgent"
        STAT = "STAT", "STAT"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        FINAL = "FINAL", "Final"

    visit = models.ForeignKey(
        "triage.Visit", on_delete=models.CASCADE, related_name="lab_requests",
    )
    lab_test = models.ForeignKey(
        LabTest, on_delete=models.RESTRICT, related_name="requests",
    )
    clinical_indication = models.TextField(blank=True, help_text="Why this test is requested")
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.ROUTINE,
    )
    result = models.TextField(blank=True)
    remarks = models.TextField(blank=True)
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
        related_name="lab_requests_created",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.lab_test.name} - {self.visit.visit_number}"

    @property
    def template(self):
        """Return the LabTestTemplate linked to this request's lab test, if any."""
        return LabTestTemplate.objects.filter(lab_test=self.lab_test).first()

    def get_structured_results(self):
        """Return dict mapping parameter_id -> result value."""
        if not self.pk:
            return {}
        return dict(
            LabTestResultValue.objects
            .filter(lab_request=self)
            .values_list("parameter_id", "value")
        )


class LabTestTemplate(IsActiveModel):
    """Defines a structured test template with ordered parameters.
    When a LabTest has a template, the technician enters results
    per-parameter instead of free text."""

    lab_test = models.OneToOneField(
        LabTest, on_delete=models.CASCADE, related_name="template",
        help_text="The lab test this template applies to",
    )
    instructions = models.TextField(
        blank=True, default="",
        help_text="Optional instructions for the technician",
    )

    class Meta:
        verbose_name = "Lab Test Template"
        verbose_name_plural = "Lab Test Templates"

    def __str__(self):
        return f"Template: {self.lab_test.name}"


class LabTestParameter(TimeStampedModel):
    """A single parameter within a lab test template (e.g., WBC, HB, PLT)."""

    template = models.ForeignKey(
        LabTestTemplate, on_delete=models.CASCADE, related_name="parameters",
    )
    name = models.CharField(
        max_length=100, help_text="Parameter name (e.g., WBC, HB, PLT)",
    )
    unit = models.CharField(max_length=50, blank=True, default="")
    normal_range = models.CharField(
        max_length=100, help_text="e.g., 4.0 - 10.0",
    )
    normal_min = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Numeric lower bound for auto-flagging",
    )
    normal_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Numeric upper bound for auto-flagging",
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Lab Test Parameter"
        verbose_name_plural = "Lab Test Parameters"

    def __str__(self):
        return f"{self.name} ({self.normal_range})"

    def flag_result(self, value_str):
        """Return ('LOW', 'HIGH', 'NORMAL', or '') based on numeric value."""
        if not value_str or self.normal_min is None or self.normal_max is None:
            return ""
        try:
            val = float(value_str)
        except (ValueError, TypeError):
            return ""
        if val < self.normal_min:
            return "LOW"
        elif val > self.normal_max:
            return "HIGH"
        return "NORMAL"


class LabTestResultValue(TimeStampedModel):
    """Stores a single parameter result for a lab request."""

    lab_request = models.ForeignKey(
        LabRequest, on_delete=models.CASCADE, related_name="result_values",
    )
    parameter = models.ForeignKey(
        LabTestParameter, on_delete=models.CASCADE, related_name="results",
    )
    value = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        unique_together = ["lab_request", "parameter"]
        verbose_name = "Lab Test Result Value"
        verbose_name_plural = "Lab Test Result Values"

    def __str__(self):
        return f"{self.parameter.name}: {self.value}"
