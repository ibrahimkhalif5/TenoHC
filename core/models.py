import string
import random
from django.conf import settings
from django.db import models
from django.db.models import Q


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class IsActiveModel(TimeStampedModel):
    """Abstract model with is_active flag."""
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class AuditLog(TimeStampedModel):
    """Track all important actions across the system."""
    class ActionType(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"
        VIEW = "VIEW", "View"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ActionType.choices)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["model_name", "object_id"]),
        ]

    def __str__(self):
        return f"{self.user} {self.action} {self.model_name}#{self.object_id}"


class HospitalSetting(models.Model):
    """Singleton hospital settings for PDF headers and branding."""
    name = models.CharField(max_length=200, default="TENOCARE HOSPITAL")
    address = models.TextField(blank=True, default="")
    telephone = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    logo = models.ImageField(upload_to="hospital/", blank=True, null=True)
    nhif_sha_rebate_per_night = models.DecimalField(
        max_digits=10, decimal_places=2, default=2240,
        help_text="NHIF/SHA bed rebate per night for insured inpatients (KSH)",
    )

    class Meta:
        verbose_name = "Hospital Setting"
        verbose_name_plural = "Hospital Settings"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


def generate_item_code():
    """Generate a unique item code: ITM-XXXX (4-char alphanumeric)."""
    while True:
        code = "ITM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if not Item.objects.filter(item_code=code).exists():
            return code


class Item(TimeStampedModel):
    """Centralized Hospital Item Master — single source of truth for all billable
    and clinical items across every module."""

    class Category(models.TextChoices):
        MEDICINE = "MEDICINE", "Medicines"
        LAB_TEST = "LAB_TEST", "Laboratory Tests"
        RADIOLOGY = "RADIOLOGY", "Radiology Services"
        ULTRASOUND = "ULTRASOUND", "Ultrasound Services"
        PROCEDURE = "PROCEDURE", "Procedures"
        NURSING = "NURSING", "Nursing Services"
        MEDICAL_SUPPLIES = "MEDICAL_SUPPLIES", "Medical Supplies"
        CONSULTATION = "CONSULTATION", "Consultation Services"
        REGISTRATION = "REGISTRATION", "Registration Services"
        WARD_CHARGES = "WARD_CHARGES", "Ward Charges"
        OTHER = "OTHER", "Other Billable Services"

    class Department(models.TextChoices):
        PHARMACY = "PHARMACY", "Pharmacy"
        LABORATORY = "LABORATORY", "Laboratory"
        RADIOLOGY = "RADIOLOGY", "Radiology"
        CONSULTATION = "CONSULTATION", "Consultation"
        NURSING = "NURSING", "Nursing"
        ADMISSSION = "ADMISSION", "Admission"
        REGISTRATION = "REGISTRATION", "Registration"
        ADMINISTRATION = "ADMINISTRATION", "Administration"
        OTHER = "OTHER", "Other"

    item_code = models.CharField(max_length=20, unique=True, default=generate_item_code, editable=False)
    name = models.CharField(max_length=300)
    category = models.CharField(max_length=30, choices=Category.choices)
    description = models.TextField(blank=True, default="")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_of_measure = models.CharField(max_length=50, default="Unit", help_text="e.g., Unit, Tablet, Test, Session, Night")
    normal_range = models.CharField(max_length=200, blank=True, default="", help_text="Reference range for lab tests (e.g., 70-100 mg/dL)")
    unit = models.CharField(max_length=50, blank=True, default="", help_text="Measurement unit for lab tests (e.g., mg/dL, x10^9/L)")
    department = models.CharField(max_length=30, choices=Department.choices, default=Department.OTHER)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="items_created",
    )

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.item_code} - {self.name}"

    def format_price(self):
        """Format price as KSH without unnecessary decimals."""
        if self.unit_price == int(self.unit_price):
            return f"KSH {int(self.unit_price):,}"
        return f"KSH {self.unit_price:,.2f}"

    @classmethod
    def search(cls, query, category=None):
        """Search items by name/code, optionally filter by category."""
        qs = cls.objects.filter(is_active=True)
        if query:
            qs = qs.filter(
                Q(name__icontains=query) |
                Q(item_code__icontains=query) |
                Q(description__icontains=query)
            )
        if category:
            qs = qs.filter(category=category)
        return qs.order_by("category", "name")
