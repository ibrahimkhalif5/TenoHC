"""
Service layer for triage app.
"""
from django.db import transaction

from .models import Visit, TriageAssessment, VisitEvent


def generate_visit_number():
    """Generate unique visit number: VIS-YYYY-NNNNNN."""
    from datetime import date
    year = date.today().year
    prefix = f"VIS-{year}-"

    with transaction.atomic():
        last = (
            Visit.objects
            .select_for_update()
            .filter(visit_number__startswith=prefix)
            .order_by("-visit_number")
            .first()
        )
        if last:
            last_seq = int(last.visit_number.split("-")[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1
        return f"{prefix}{next_seq:06d}"


def log_visit_event(visit, event_type, description="", user=None):
    """Log a workflow event for a visit."""
    VisitEvent.objects.create(
        visit=visit,
        event_type=event_type,
        description=description,
        created_by=user,
    )


def get_triage_queue():
    """Get all visits waiting for triage."""
    return (
        Visit.objects
        .filter(status=Visit.Status.WAITING_TRIAGE)
        .select_related("patient", "patient__patient_category")
        .order_by("created_at")
    )


def get_visit(visit_id):
    """Get visit with patient and assessments prefetched."""
    return (
        Visit.objects
        .select_related("patient", "patient__patient_category", "created_by")
        .prefetch_related("triage_assessments", "events")
        .get(pk=visit_id)
    )


def get_visit_timeline(visit):
    """Get ordered timeline events for a visit."""
    return visit.events.select_related("created_by").order_by("timestamp")


def complete_triage(visit_id, form_data, user=None):
    """
    Complete triage assessment and release patient to doctor.
    Creates TriageAssessment + changes Visit status to WAITING_DOCTOR.
    """
    with transaction.atomic():
        visit = Visit.objects.select_for_update().get(pk=visit_id)

        assessment = TriageAssessment.objects.create(
            visit=visit,
            temperature=form_data["temperature"],
            weight=form_data["weight"],
            height=form_data["height"],
            blood_pressure_systolic=form_data["blood_pressure_systolic"],
            blood_pressure_diastolic=form_data["blood_pressure_diastolic"],
            pulse=form_data["pulse"],
            respiratory_rate=form_data["respiratory_rate"],
            oxygen_saturation=form_data["oxygen_saturation"],
            chief_complaint=form_data["chief_complaint"],
            nurse_notes=form_data.get("nurse_notes", ""),
            assessed_by=user,
        )

        visit.status = Visit.Status.WAITING_DOCTOR
        visit.save(update_fields=["status", "updated_at"])

        log_visit_event(visit, "Triage Completed",
                        f"Vitals recorded. Chief complaint: {form_data['chief_complaint']}",
                        user=user)

        return assessment


def release_to_doctor(visit, user=None):
    """Change visit status to WAITING_DOCTOR."""
    visit.status = Visit.Status.WAITING_DOCTOR
    visit.save(update_fields=["status", "updated_at"])
    return visit
