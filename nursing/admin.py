from django.contrib import admin
from .models import NursingNote, DailyVitals, Treatment


@admin.register(NursingNote)
class NursingNoteAdmin(admin.ModelAdmin):
    list_display = ("admission", "note", "created_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("admission__patient__first_name", "admission__patient__last_name", "note")


@admin.register(DailyVitals)
class DailyVitalsAdmin(admin.ModelAdmin):
    list_display = (
        "admission", "record_date", "temperature",
        "blood_pressure_systolic", "blood_pressure_diastolic",
        "pulse", "oxygen_saturation", "recorded_by",
    )
    list_filter = ("record_date",)
    search_fields = ("admission__patient__first_name", "admission__patient__last_name")


@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ("admission", "treatment", "medication", "dosage", "frequency", "given_by")
    list_filter = ("given_by",)
    search_fields = ("admission__patient__first_name", "admission__patient__last_name", "treatment")
