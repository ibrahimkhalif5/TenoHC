from django.contrib import admin
from .models import Ward, Room, Bed, Admission


class BedInline(admin.TabularInline):
    model = Bed
    extra = 1


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ("name", "ward_type", "price_per_night", "is_active")
    list_filter = ("ward_type", "is_active")
    search_fields = ("name",)
    list_editable = ("price_per_night", "is_active")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "ward", "room_type", "capacity", "is_occupied", "is_active")
    list_filter = ("ward", "room_type", "is_occupied", "is_active")
    search_fields = ("room_number",)
    list_editable = ("is_occupied", "is_active")


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ("bed_number", "room", "is_occupied", "is_active")
    list_filter = ("is_occupied", "is_active")
    search_fields = ("bed_number",)
    list_editable = ("is_occupied", "is_active")


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = (
        "patient", "visit", "ward", "room", "bed",
        "admission_date", "discharge_date", "status",
        "admitted_by", "discharged_by",
    )
    list_filter = ("status", "ward__ward_type", "admission_date")
    search_fields = (
        "patient__first_name", "patient__last_name",
        "visit__visit_number", "patient__patient_number",
    )
    readonly_fields = ("admission_date", "created_at", "updated_at")
