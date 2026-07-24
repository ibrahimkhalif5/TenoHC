from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        DOCTOR = "DOCTOR", "Doctor"
        NURSE = "NURSE", "Nurse"
        PHARMACIST = "PHARMACIST", "Pharmacist"
        LAB_TECHNICIAN = "LAB_TECHNICIAN", "Lab Technician"
        RADIOLOGIST = "RADIOLOGIST", "Radiologist"
        RECEPTIONIST = "RECEPTIONIST", "Receptionist"
        CASHIER = "CASHIER", "Cashier"
        INVENTORY_MANAGER = "INVENTORY_MANAGER", "Inventory Manager"
        WARD_MANAGER = "WARD_MANAGER", "Ward Manager"

    phone_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.RECEPTIONIST,
    )

    class Meta:
        verbose_name_plural = "users"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.get_full_name() or self.username

    def get_full_name_or_username(self):
        return self.get_full_name() or self.username
