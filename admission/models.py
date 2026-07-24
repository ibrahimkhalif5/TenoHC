from datetime import date
from django.db import models
from django.conf import settings
from core.models import TimeStampedModel, IsActiveModel


class Ward(IsActiveModel):
    """Hospital ward (Executive, General, VIP, etc.)."""

    class WardType(models.TextChoices):
        EXECUTIVE = "EXECUTIVE", "Executive Ward"
        GENERAL = "GENERAL", "General Ward"
        VIP = "VIP", "VIP Ward"

    item = models.ForeignKey(
        "core.Item", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="wards", help_text="Linked Item Master entry",
    )
    name = models.CharField(max_length=100)
    ward_type = models.CharField(max_length=20, choices=WardType.choices)
    description = models.TextField(blank=True)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["ward_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_ward_type_display()})"

    @property
    def available_beds(self):
        from django.db.models import Q
        return Bed.objects.filter(
            room__ward=self, is_occupied=False, is_active=True,
        ).count()

    @property
    def total_beds(self):
        return Bed.objects.filter(
            room__ward=self, is_active=True,
        ).count()


class Room(IsActiveModel):
    """Room within a ward."""

    class RoomType(models.TextChoices):
        SINGLE = "SINGLE", "Single"
        DOUBLE = "DOUBLE", "Double"
        SHARED = "SHARED", "Shared"

    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=20)
    room_type = models.CharField(max_length=20, choices=RoomType.choices, default=RoomType.SINGLE)
    capacity = models.PositiveIntegerField(default=1)
    is_occupied = models.BooleanField(default=False)

    class Meta:
        ordering = ["ward", "room_number"]
        unique_together = ["ward", "room_number"]

    def __str__(self):
        return f"Room {self.room_number} - {self.ward.name}"

    @property
    def available_beds(self):
        return self.beds.filter(is_occupied=False, is_active=True).count()


class Bed(IsActiveModel):
    """Bed within a room."""

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="beds")
    bed_number = models.CharField(max_length=20)
    is_occupied = models.BooleanField(default=False)

    class Meta:
        ordering = ["room", "bed_number"]
        unique_together = ["room", "bed_number"]

    def __str__(self):
        return f"Bed {self.bed_number} - Room {self.room.room_number}"


class Admission(TimeStampedModel):
    """Patient admission record."""

    class Status(models.TextChoices):
        ADMITTED = "ADMITTED", "Admitted"
        DISCHARGED = "DISCHARGED", "Discharged"

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="admissions",
    )
    visit = models.ForeignKey(
        "triage.Visit", on_delete=models.CASCADE, related_name="admissions",
    )
    ward = models.ForeignKey(Ward, on_delete=models.RESTRICT, related_name="admissions")
    room = models.ForeignKey(Room, on_delete=models.RESTRICT, related_name="admissions")
    bed = models.ForeignKey(Bed, on_delete=models.RESTRICT, related_name="admissions")

    admission_date = models.DateField(default=date.today)
    discharge_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ADMITTED,
    )

    diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    admitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="admissions_created",
    )
    discharged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="admissions_discharged",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Admission: {self.patient.full_name} - {self.ward.name} ({self.get_status_display()})"

    @property
    def nights_stayed(self):
        if self.discharge_date:
            delta = self.discharge_date - self.admission_date
            return max(delta.days, 1)
        today = date.today()
        delta = today - self.admission_date
        return max(delta.days, 0)

    @property
    def ward_charge(self):
        return self.nights_stayed * self.ward.price_per_night
