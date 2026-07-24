from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "model_name", "object_id", "object_repr")
    list_filter = ("action", "model_name", "created_at")
    search_fields = ("object_repr", "description", "user__username")
    readonly_fields = ("user", "action", "model_name", "object_id", "object_repr", "description", "ip_address", "created_at")
    date_hierarchy = "created_at"
