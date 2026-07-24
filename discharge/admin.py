from django.contrib import admin
from .models import DischargeSummary, DischargeMedication


class DischargeMedicationInline(admin.TabularInline):
    model = DischargeMedication
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


@admin.register(DischargeSummary)
class DischargeSummaryAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "patient_name",
        "admission_id",
        "status",
        "primary_diagnosis",
        "created_by",
        "finalized_by",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = [
        "admission__patient__first_name",
        "admission__patient__last_name",
        "admission__patient__patient_number",
        "primary_diagnosis",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "finalized_at",
        "finalized_by",
    ]
    inlines = [DischargeMedicationInline]

    def patient_name(self, obj):
        return obj.admission.patient.full_name
    patient_name.short_description = "Patient"


@admin.register(DischargeMedication)
class DischargeMedicationAdmin(admin.ModelAdmin):
    list_display = [
        "medicine_name",
        "dosage",
        "frequency",
        "duration",
        "discharge_summary",
    ]
    search_fields = ["medicine_name"]
