from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class Invoice(TimeStampedModel):
    """Patient invoice."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="invoices",
    )
    visit = models.ForeignKey(
        "triage.Visit", on_delete=models.CASCADE, related_name="invoices",
    )
    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nhif_rebate = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="NHIF/SHA rebate amount")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    payment_method = models.CharField(max_length=50, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.invoice_number} - {self.patient.full_name}"

    @property
    def balance(self):
        return self.total_amount - self.nhif_rebate - self.amount_paid

    @property
    def outstanding(self):
        return max(self.total_amount - self.nhif_rebate - self.amount_paid, 0)


class InvoiceItem(TimeStampedModel):
    """Line item on an invoice."""
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="items",
    )
    item = models.ForeignKey(
        "core.Item", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invoice_items", help_text="Linked Item Master entry",
    )
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    class Meta:
        verbose_name_plural = "invoice items"

    def __str__(self):
        return f"{self.description} x{self.quantity}"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
