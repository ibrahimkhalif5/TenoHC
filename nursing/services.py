"""
Service layer for nursing app.
"""
from django.db import transaction

from .models import NursingNote, DailyVitals, Treatment
from admission.models import Admission


def get_admitted_patients():
    """Get all currently admitted patients with ward info."""
    return (
        Admission.objects
        .filter(status=Admission.Status.ADMITTED)
        .select_related("patient", "ward", "room", "bed", "visit")
        .order_by("-admission_date")
    )


def get_admission_detail(admission_id):
    """Get admission with all nursing data prefetched."""
    return (
        Admission.objects
        .select_related("patient", "ward", "room", "bed", "visit", "admitted_by")
        .prefetch_related("nursing_notes__created_by", "daily_vitals__recorded_by", "treatments__given_by")
        .get(pk=admission_id)
    )


def add_nursing_note(admission_id, note, user=None):
    """Add a nursing note."""
    return NursingNote.objects.create(
        admission_id=admission_id,
        note=note,
        created_by=user,
    )


def add_daily_vitals(admission_id, data, user=None):
    """Record daily vitals."""
    return DailyVitals.objects.create(
        admission_id=admission_id,
        temperature=data["temperature"],
        blood_pressure_systolic=data["blood_pressure_systolic"],
        blood_pressure_diastolic=data["blood_pressure_diastolic"],
        pulse=data["pulse"],
        respiratory_rate=data["respiratory_rate"],
        oxygen_saturation=data["oxygen_saturation"],
        weight=data.get("weight"),
        notes=data.get("notes", ""),
        recorded_by=user,
    )


def add_treatment(admission_id, data, user=None):
    """Record a treatment given."""
    return Treatment.objects.create(
        admission_id=admission_id,
        treatment=data["treatment"],
        medication=data.get("medication", ""),
        dosage=data.get("dosage", ""),
        frequency=data.get("frequency", ""),
        notes=data.get("notes", ""),
        given_by=user,
    )
