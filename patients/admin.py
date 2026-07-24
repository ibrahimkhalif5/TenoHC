from django.contrib import admin
from .models import PatientCategory, Patient


@admin.register(PatientCategory)
class PatientCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "discount_percentage", "is_active")
    list_filter = ("is_active",)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "patient_number", "first_name", "last_name", "gender",
        "phone", "patient_type", "payment_type", "is_active",
    )
    search_fields = ("patient_number", "first_name", "last_name", "phone", "national_id")
    list_filter = ("gender", "patient_type", "payment_type", "is_active")
    readonly_fields = ("patient_number", "created_at", "updated_at")
