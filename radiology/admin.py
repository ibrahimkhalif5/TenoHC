from django.contrib import admin
from .models import RadiologyService, RadiologyRequest


@admin.register(RadiologyService)
class RadiologyServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "service_type", "body_part", "price", "is_active")
    list_filter = ("service_type", "is_active")
    search_fields = ("name", "body_part")
    list_editable = ("price", "is_active")


@admin.register(RadiologyRequest)
class RadiologyRequestAdmin(admin.ModelAdmin):
    list_display = (
        "visit", "radiology_service", "priority", "is_completed",
        "requested_by", "completed_by", "completed_at",
    )
    list_filter = ("priority", "is_completed", "radiology_service__service_type")
    search_fields = ("visit__visit_number", "visit__patient__first_name", "visit__patient__last_name")
    readonly_fields = ("completed_at", "created_at", "updated_at")
