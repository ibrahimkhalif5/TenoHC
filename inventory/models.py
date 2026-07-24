from datetime import date
from django.db import models
from django.conf import settings
from core.models import TimeStampedModel, IsActiveModel


class MedicineCategory(IsActiveModel):
    """Category for medicines (Antibiotics, Analgesics, etc.)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "medicine categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Supplier(IsActiveModel):
    """Medicine supplier/pharmacy vendor."""
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Medicine(IsActiveModel):
    """Master data: a medicine/drug."""

    class DosageForm(models.TextChoices):
        TABLET = "TABLET", "Tablet"
        CAPSULE = "CAPSULE", "Capsule"
        SYRUP = "SYRUP", "Syrup"
        INJECTION = "INJECTION", "Injection"
        CREAM = "CREAM", "Cream"
        OINTMENT = "OINTMENT", "Ointment"
        DROPS = "DROPS", "Drops"
        INHALER = "INHALER", "Inhaler"
        SUPPOSITORY = "SUPPOSITORY", "Suppository"
        OTHER = "OTHER", "Other"

    item = models.ForeignKey(
        "core.Item", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="medicines", help_text="Linked Item Master entry",
    )
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(
        MedicineCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="medicines",
    )
    dosage_form = models.CharField(max_length=20, choices=DosageForm.choices, default=DosageForm.TABLET)
    strength = models.CharField(max_length=100, blank=True, help_text="e.g. 500mg, 10ml")
    unit = models.CharField(max_length=50, default="pcs", help_text="pcs, bottles, tubes, etc.")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_stock = models.PositiveIntegerField(default=10, help_text="Alert when stock falls below this")
    reorder_level = models.PositiveIntegerField(default=20, help_text="Suggested reorder point")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.strength})" if self.strength else self.name

    @property
    def current_stock(self):
        """Total stock across all batches."""
        return self.stocks.aggregate(
            total=models.Sum("quantity")
        )["total"] or 0

    @property
    def is_low_stock(self):
        return self.current_stock < self.minimum_stock

    @property
    def is_expired_stock(self):
        return self.stocks.filter(
            expiry_date__lt=date.today(), quantity__gt=0,
        ).exists()

    @property
    def nearest_expiry(self):
        stock = self.stocks.filter(
            expiry_date__gte=date.today(), quantity__gt=0,
        ).order_by("expiry_date").first()
        return stock.expiry_date if stock else None


class Purchase(TimeStampedModel):
    """Purchase/procurement record from a supplier."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RECEIVED = "RECEIVED", "Received"
        CANCELLED = "CANCELLED", "Cancelled"

    supplier = models.ForeignKey(
        Supplier, on_delete=models.RESTRICT, related_name="purchases",
    )
    purchase_date = models.DateField()
    invoice_number = models.CharField(max_length=100, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    notes = models.TextField(blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        ordering = ["-purchase_date", "-created_at"]

    def __str__(self):
        return f"Purchase #{self.pk} - {self.supplier.name} ({self.get_status_display()})"


class PurchaseItem(TimeStampedModel):
    """Line item in a purchase order."""
    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, related_name="items",
    )
    medicine = models.ForeignKey(
        Medicine, on_delete=models.RESTRICT, related_name="purchase_items",
    )
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    batch_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField()

    class Meta:
        verbose_name_plural = "purchase items"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.medicine.name} x{self.quantity}"

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update purchase total
        purchase = self.purchase
        purchase.total_amount = sum(item.total_cost for item in purchase.items.all())
        purchase.save(update_fields=["total_amount", "updated_at"])


class Stock(TimeStampedModel):
    """Stock level for a medicine batch."""

    medicine = models.ForeignKey(
        Medicine, on_delete=models.CASCADE, related_name="stocks",
    )
    batch_number = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=0)
    expiry_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["expiry_date"]
        unique_together = ["medicine", "batch_number"]

    def __str__(self):
        return f"{self.medicine.name} - Batch {self.batch_number} ({self.quantity} units)"

    @property
    def is_expired(self):
        return self.expiry_date < date.today()

    @property
    def days_until_expiry(self):
        delta = self.expiry_date - date.today()
        return max(delta.days, 0)


class StockMovement(TimeStampedModel):
    """Audit trail for all stock changes."""

    class MovementType(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase (Stock In)"
        DISPENSE = "DISPENSE", "Dispense (Stock Out)"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        RETURN = "RETURN", "Return"
        EXPIRED = "EXPIRED", "Expired/Disposed"

    medicine = models.ForeignKey(
        Medicine, on_delete=models.CASCADE, related_name="stock_movements",
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.IntegerField(help_text="Positive for IN, negative for OUT")
    batch_number = models.CharField(max_length=100, blank=True)
    reference = models.CharField(max_length=200, blank=True, help_text="Purchase #, Patient #, etc.")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.quantity > 0 else ""
        return f"{self.medicine.name}: {sign}{self.quantity} ({self.get_movement_type_display()})"
