from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class Payment(TimeStampedModel):
    """Payment transaction against an invoice."""

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        MPESA = "MPESA", "M-Pesa"
        BANK = "BANK", "Bank Transfer"
        CARD = "CARD", "Card"
        INSURANCE = "INSURANCE", "Insurance"

    invoice = models.ForeignKey(
        "billing.Invoice", on_delete=models.CASCADE, related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    reference_number = models.CharField(max_length=100, blank=True, help_text="Transaction reference")
    receipt_number = models.CharField(max_length=20, unique=True, editable=False)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.receipt_number} - KSh {self.amount:,.2f} ({self.get_payment_method_display()})"
