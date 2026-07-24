"""
Service layer for admission app.
"""
from datetime import date
from django.db import transaction
from django.utils import timezone

from .models import Ward, Room, Bed, Admission


# ─── Ward / Room / Bed helpers ────────────────────────────────────────

def get_all_wards():
    return Ward.objects.filter(is_active=True)


def get_ward(ward_id):
    return Ward.objects.get(pk=ward_id)


def get_available_rooms(ward_id):
    return Room.objects.filter(ward_id=ward_id, is_active=True, is_occupied=False)


def get_available_beds(room_id):
    return Bed.objects.filter(room_id=room_id, is_active=True, is_occupied=False)


# ─── Admission queue ─────────────────────────────────────────────────

def get_admission_queue():
    """Get all visits waiting for admission."""
    from triage.models import Visit
    return (
        Visit.objects
        .filter(status=Visit.Status.ADMISSION_IN_PROGRESS)
        .select_related("patient", "patient__patient_category")
        .order_by("created_at")
    )


def get_admitted_patients():
    """Get all currently admitted patients."""
    return (
        Admission.objects
        .filter(status=Admission.Status.ADMITTED)
        .select_related("patient", "ward", "room", "bed", "visit")
        .order_by("-admission_date")
    )


def get_visit_admission(visit_id):
    """Get admission for a specific visit."""
    return Admission.objects.filter(visit_id=visit_id).first()


# ─── Admit patient ────────────────────────────────────────────────────

def admit_patient(visit_id, ward_id, room_id, bed_id, diagnosis="", notes="", user=None):
    """
    Admit a patient in one step.
    Assigns ward/room/bed, marks bed as occupied, updates visit status.
    Ward charges are billed on discharge, not on admission.
    """
    from triage.models import Visit

    with transaction.atomic():
        visit = Visit.objects.select_for_update().get(pk=visit_id)
        ward = Ward.objects.get(pk=ward_id)
        room = Room.objects.select_for_update().get(pk=room_id, ward=ward)
        bed = Bed.objects.select_for_update().get(pk=bed_id, room=room, is_occupied=False)

        # Mark bed and room as occupied
        bed.is_occupied = True
        bed.save(update_fields=["is_occupied", "updated_at"])

        room.is_occupied = True
        room.save(update_fields=["is_occupied", "updated_at"])

        # Create admission
        admission = Admission.objects.create(
            patient=visit.patient,
            visit=visit,
            ward=ward,
            room=room,
            bed=bed,
            diagnosis=diagnosis,
            notes=notes,
            admitted_by=user,
        )

        # Update visit status to completed (admitted patients don't stay in queue)
        visit.status = Visit.Status.COMPLETED
        visit.save(update_fields=["status", "updated_at"])

        return admission


# ─── Discharge patient ────────────────────────────────────────────────

def discharge_patient(admission_id, user=None):
    """
    Discharge a patient.
    Calculates total ward charge (nights × ward price), creates invoice item,
    frees bed/room, updates admission and visit status.
    """
    from triage.models import Visit
    from billing.services import get_or_create_visit_invoice, add_invoice_item

    with transaction.atomic():
        admission = Admission.objects.select_for_update().get(pk=admission_id)

        # Calculate nights
        today = date.today()
        delta = today - admission.admission_date
        nights = max(delta.days, 1)

        total_charge = nights * admission.ward.price_per_night

        # Update admission
        admission.discharge_date = today
        admission.status = Admission.Status.DISCHARGED
        admission.discharged_by = user
        admission.save(update_fields=[
            "discharge_date", "status", "discharged_by", "updated_at",
        ])

        # Free bed and room
        admission.bed.is_occupied = False
        admission.bed.save(update_fields=["is_occupied", "updated_at"])

        # Check if room is now empty
        room = admission.room
        if not room.beds.filter(is_occupied=True, is_active=True).exists():
            room.is_occupied = False
            room.save(update_fields=["is_occupied", "updated_at"])

        # Update visit status
        visit = admission.visit
        visit.status = Visit.Status.DISCHARGED
        visit.save(update_fields=["status", "updated_at"])

        # Bill: add total ward charge (nights x price_per_night)
        invoice = get_or_create_visit_invoice(visit, user)
        add_invoice_item(
            invoice,
            description=f"Ward: {admission.ward.name} ({nights} night{'s' if nights != 1 else ''})",
            quantity=nights,
            unit_price=admission.ward.price_per_night,
        )

        return admission, nights, total_charge
