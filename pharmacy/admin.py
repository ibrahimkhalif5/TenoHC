from django.contrib import admin
from .models import PharmacyDispense


@admin.register(PharmacyDispense)
class PharmacyDispenseAdmin(admin.ModelAdmin):
    list_display = (
        "medicine", "quantity_dispensed", "visit", "charge",
        "dispensed_by", "dispensed_at",
    )
    list_filter = ("dispensed_at",)
    search_fields = (
        "visit__visit_number", "visit__patient__first_name",
        "visit__patient__last_name", "medicine__name",
    )
    readonly_fields = ("dispensed_at", "created_at", "updated_at")
