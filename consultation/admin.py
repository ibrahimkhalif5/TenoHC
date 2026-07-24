from django.contrib import admin
from .models import Consultation, Prescription


class PrescriptionInline(admin.TabularInline):
    model = Prescription
    extra = 1
    fields = ("medicine", "dosage", "dosage_unit", "frequency", "duration_days", "quantity", "is_dispensed")
    readonly_fields = ("is_dispensed",)
    autocomplete_fields = ("medicine",)


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    inlines = [PrescriptionInline]
    list_display = (
        "visit", "doctor", "diagnosis", "consultation_fee",
        "status", "started_at", "completed_at",
    )
    list_filter = ("status",)
    search_fields = (
        "visit__visit_number",
        "visit__patient__first_name",
        "visit__patient__last_name",
        "doctor__username",
        "diagnosis",
    )
    readonly_fields = ("started_at", "completed_at", "created_at", "updated_at")


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = (
        "consultation", "medicine", "dosage", "dosage_unit",
        "frequency", "duration_days", "quantity", "is_dispensed",
    )
    list_filter = ("is_dispensed", "dosage_unit")
    search_fields = (
        "consultation__visit__visit_number",
        "medicine__name",
    )
