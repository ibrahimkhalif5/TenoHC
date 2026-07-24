"""
Service layer for the discharge summary module.
"""
from datetime import date
from django.db import transaction
from django.utils import timezone

from .models import DischargeSummary, DischargeMedication


def get_discharge_summary(admission_id):
    """Get or return None for a discharge summary linked to an admission."""
    return DischargeSummary.objects.filter(admission_id=admission_id).first()


def create_discharge_summary(admission_id, user=None):
    """Create a new draft discharge summary for an admission."""
    from admission.models import Admission

    with transaction.atomic():
        admission = Admission.objects.select_for_update().get(pk=admission_id)

        existing = DischargeSummary.objects.filter(admission=admission).first()
        if existing:
            return existing

        summary = DischargeSummary.objects.create(
            admission=admission,
            created_by=user,
        )
        return summary


def save_draft(summary_id, data, user=None):
    """Save discharge summary draft fields."""
    with transaction.atomic():
        summary = DischargeSummary.objects.select_for_update().get(pk=summary_id)

        text_fields = [
            "primary_diagnosis",
            "secondary_diagnosis",
            "reason_for_admission",
            "history_of_present_illness",
            "clinical_findings",
            "investigations_performed",
            "procedures_done",
            "treatment_given",
            "patient_progress",
            "condition_on_discharge",
            "doctor_advice",
            "lifestyle_advice",
            "diet_advice",
            "activity_restrictions",
            "warning_signs",
        ]
        update_fields = []
        for field in text_fields:
            if field in data:
                setattr(summary, field, data[field])
                update_fields.append(field)

        follow_up_date = data.get("follow_up_date", "")
        if follow_up_date:
            summary.follow_up_date = follow_up_date
            update_fields.append("follow_up_date")
        elif "follow_up_date" in data:
            summary.follow_up_date = None
            update_fields.append("follow_up_date")

        if "doctor_signature" in data:
            summary.doctor_signature = data["doctor_signature"]
            update_fields.append("doctor_signature")

        update_fields.append("updated_at")
        summary.save(update_fields=update_fields)
        return summary


def finalize_discharge_summary(summary_id, user=None):
    """Finalize the discharge summary and perform discharge actions."""
    from admission.models import Admission
    from admission.services import discharge_patient

    with transaction.atomic():
        summary = DischargeSummary.objects.select_for_update().get(pk=summary_id)

        validation_errors = summary.can_finalize()
        if validation_errors:
            return summary, validation_errors

        summary.status = DischargeSummary.Status.FINALIZED
        summary.finalized_by = user
        summary.finalized_at = timezone.now()
        summary.save(update_fields=[
            "status", "finalized_by", "finalized_at", "updated_at",
        ])

        admission = summary.admission
        if admission.status == Admission.Status.ADMITTED:
            discharge_patient(admission_id=admission.pk, user=user)

        return summary, []


def get_all_discharge_summaries():
    """Get all discharge summaries with related data."""
    return (
        DischargeSummary.objects
        .select_related(
            "admission",
            "admission__patient",
            "admission__ward",
            "admission__room",
            "admission__bed",
            "admission__visit",
            "created_by",
            "finalized_by",
        )
        .order_by("-created_at")
    )


def get_patient_discharge_summaries(patient_id):
    """Get discharge summaries for a specific patient."""
    return (
        DischargeSummary.objects
        .filter(admission__patient_id=patient_id)
        .select_related(
            "admission",
            "admission__ward",
            "admission__room",
            "admission__bed",
        )
        .order_by("-created_at")
    )


def add_discharge_medication(summary_id, data):
    """Add a discharge medication to a summary."""
    summary = DischargeSummary.objects.get(pk=summary_id)
    return DischargeMedication.objects.create(
        discharge_summary=summary,
        medicine_name=data["medicine_name"],
        dosage=data.get("dosage", ""),
        frequency=data.get("frequency", ""),
        duration=data.get("duration", ""),
        instructions=data.get("instructions", ""),
    )


def remove_discharge_medication(medication_id):
    """Remove a discharge medication."""
    DischargeMedication.objects.filter(pk=medication_id).delete()


def get_investigations_for_visit(visit):
    """Retrieve lab and radiology investigations for a visit."""
    from laboratory.models import LabRequest
    from radiology.models import RadiologyRequest

    labs = LabRequest.objects.filter(visit=visit).select_related("lab_test")
    rads = RadiologyRequest.objects.filter(visit=visit).select_related("radiology_service")

    return labs, rads


def get_treatments_for_admission(admission):
    """Retrieve nursing treatments for an admission."""
    from nursing.models import Treatment
    return Treatment.objects.filter(admission=admission)


def get_prescriptions_for_visit(visit):
    """Retrieve prescriptions from consultations for a visit."""
    from consultation.models import Prescription
    return (
        Prescription.objects
        .filter(consultation__visit=visit)
        .select_related("medicine")
    )
