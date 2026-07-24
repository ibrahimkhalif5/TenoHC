from django.contrib import admin
from .models import LabTest, LabRequest


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "turnaround_time", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name",)
    list_editable = ("price", "is_active")


@admin.register(LabRequest)
class LabRequestAdmin(admin.ModelAdmin):
    list_display = (
        "visit", "lab_test", "priority", "is_completed",
        "requested_by", "completed_by", "completed_at",
    )
    list_filter = ("priority", "is_completed", "lab_test__category")
    search_fields = ("visit__visit_number", "visit__patient__first_name", "visit__patient__last_name")
    readonly_fields = ("completed_at", "created_at", "updated_at")
