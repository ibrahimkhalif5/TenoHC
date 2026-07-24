from django.contrib import admin
from .models import Visit, TriageAssessment


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("visit_number", "patient", "status", "visit_date", "created_by")
    list_filter = ("status", "visit_date")
    search_fields = ("visit_number", "patient__patient_number", "patient__first_name", "patient__last_name")
    readonly_fields = ("visit_number", "visit_date", "created_at", "updated_at")


@admin.register(TriageAssessment)
class TriageAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "visit", "temperature", "blood_pressure_systolic", "blood_pressure_diastolic",
        "pulse", "oxygen_saturation", "assessed_by", "assessed_at",
    )
    list_filter = ("assessed_at",)
    readonly_fields = ("assessed_at", "created_at", "updated_at")
