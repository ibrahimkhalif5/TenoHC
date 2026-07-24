from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import IsActiveModel


class PatientCategory(IsActiveModel):
    """Patient category (VIP, HMO, Staff, etc.)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    class Meta:
        verbose_name_plural = "patient categories"

    def __str__(self):
        return self.name


class Patient(IsActiveModel):
    """Hospital patient record."""

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    class PatientType(models.TextChoices):
        NEW = "NEW", "New Patient"
        RETURNING = "RETURNING", "Returning Patient"

    class PaymentType(models.TextChoices):
        CASH = "CASH", "Cash"
        INSURANCE = "INSURANCE", "Insurance"

    # Identifiers
    patient_number = models.CharField(max_length=20, unique=True, editable=False)
    photo = models.ImageField(upload_to="patients/photos/", blank=True, null=True)
    national_id = models.CharField(max_length=50, unique=True, blank=True, null=True)

    # Personal information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    date_of_birth = models.DateField()
    phone = models.CharField(max_length=20)
    address = models.TextField()

    # Next of kin
    next_of_kin_name = models.CharField(max_length=200, blank=True, default="")
    next_of_kin_phone = models.CharField(max_length=20, blank=True, default="")
    next_of_kin_relationship = models.CharField(max_length=100, blank=True)

    # Registration details
    patient_category = models.ForeignKey(
        PatientCategory, on_delete=models.SET_NULL, null=True, blank=True,
    )
    patient_type = models.CharField(
        max_length=20, choices=PatientType.choices, default=PatientType.NEW,
    )
    payment_type = models.CharField(
        max_length=20, choices=PaymentType.choices, default=PaymentType.INSURANCE,
    )
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.patient_number} - {self.full_name}"

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p).strip()

    @property
    def age(self):
        from datetime import date
        today = date.today()
        return (
            today.year - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )
