"""
Service layer for consultation app.
Handles doctor consultations, test ordering, prescriptions, and the
patient routing workflow.
"""
from datetime import date
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from core.constants import DOCTOR_NAME

from .models import Consultation, Prescription


# ─── Queue helpers ──────────────────────────────────────────────────

def get_doctor_queue():
    """Get all visits waiting for or in consultation with the doctor."""
    from triage.models import Visit
    return (
        Visit.objects
        .filter(status__in=[
            Visit.Status.WAITING_DOCTOR,
            Visit.Status.WAITING_DOCTOR_REVIEW,
            Visit.Status.IN_CONSULTATION,
        ])
        .select_related("patient", "patient__patient_category")
        .order_by("created_at")
    )


def get_visit_consultations(visit):
    """Get all consultations for a visit."""
    return (
        Consultation.objects
        .filter(visit=visit)
        .select_related("doctor")
        .prefetch_related("prescriptions", "prescriptions__medicine")
        .order_by("-started_at")
    )


# ─── Start consultation ────────────────────────────────────────────

def start_consultation(visit_id, user=None):
    """
    Start a consultation. Accepts WAITING_DOCTOR, WAITING_DOCTOR_REVIEW,
    and IN_CONSULTATION (returns existing consultation).
    """
    from triage.models import Visit
    from triage.services import log_visit_event

    with transaction.atomic():
        visit = Visit.objects.select_for_update().get(pk=visit_id)

        if visit.status == Visit.Status.IN_CONSULTATION:
            existing = Consultation.objects.filter(
                visit=visit, status=Consultation.Status.IN_PROGRESS,
            ).order_by("-started_at").first()
            if existing:
                return existing
            # Stale IN_CONSULTATION status with no active consultation — reset
            visit.status = Visit.Status.WAITING_DOCTOR
            visit.save(update_fields=["status", "updated_at"])

        if visit.status not in (
            Visit.Status.WAITING_DOCTOR,
            Visit.Status.WAITING_DOCTOR_REVIEW,
        ):
            raise ValueError(
                f"Cannot start consultation. Patient status is "
                f"'{visit.get_status_display()}'."
            )

        was_review = visit.status == Visit.Status.WAITING_DOCTOR_REVIEW

        if was_review:
            consultation = Consultation.objects.filter(
                visit=visit, status=Consultation.Status.IN_PROGRESS,
            ).order_by("-started_at").first()
            if not consultation:
                consultation = Consultation.objects.create(
                    visit=visit,
                    doctor=user,
                    status=Consultation.Status.IN_PROGRESS,
                )
        else:
            consultation = Consultation.objects.create(
                visit=visit,
                doctor=user,
                status=Consultation.Status.IN_PROGRESS,
            )

        visit.status = Visit.Status.IN_CONSULTATION
        visit.save(update_fields=["status", "updated_at"])

        if was_review:
            log_visit_event(
                visit, "Doctor Review Started",
                "Doctor is reviewing diagnostic results.",
                user=user,
            )
        else:
            log_visit_event(
                visit, "Consultation Started",
                f"Consultation #{consultation.pk} started by {user}.",
                user=user,
            )

        return consultation


# ─── Order tests (keeps consultation IN_PROGRESS) ──────────────────

def order_tests(consultation_id, lab_test_ids=None, radiology_service_ids=None,
                diagnosis="", notes="", user=None):
    """
    Order laboratory and/or radiology tests without completing the consultation.
    The consultation stays IN_PROGRESS. The visit moves to the appropriate queue.
    """
    from triage.models import Visit
    from triage.services import log_visit_event
    from laboratory.services import create_lab_request
    from radiology.services import create_radiology_request

    with transaction.atomic():
        consultation = Consultation.objects.select_for_update().get(pk=consultation_id)
        visit = consultation.visit

        if consultation.status != Consultation.Status.IN_PROGRESS:
            raise ValueError("Consultation is not in progress.")

        if diagnosis:
            consultation.diagnosis = diagnosis
        if notes:
            consultation.notes = notes
        consultation.save(update_fields=["diagnosis", "notes", "updated_at"])

        lab_count = 0
        rad_count = 0

        if lab_test_ids:
            for test_id in lab_test_ids:
                create_lab_request(visit.id, test_id, user=user)
                lab_count += 1

        if radiology_service_ids:
            for svc_id in radiology_service_ids:
                create_radiology_request(visit.id, svc_id, user=user)
                rad_count += 1

        parts = []
        if lab_count:
            parts.append(f"{lab_count} lab test(s)")
        if rad_count:
            parts.append(f"{rad_count} radiology order(s)")

        desc = f"Ordered: {', '.join(parts)}" if parts else "No tests ordered"

        if lab_count and visit.status == Visit.Status.IN_CONSULTATION:
            visit.status = Visit.Status.WAITING_LAB
            visit.save(update_fields=["status", "updated_at"])
        elif rad_count and visit.status == Visit.Status.IN_CONSULTATION:
            visit.status = _determine_radiology_status(visit)
            visit.save(update_fields=["status", "updated_at"])

        log_visit_event(visit, "Tests Ordered", desc, user=user)

        return consultation, lab_count, rad_count


def _determine_radiology_status(visit):
    """Determine whether to send to XRAY or ULTRASOUND queue."""
    from radiology.models import RadiologyRequest
    pending = RadiologyRequest.objects.filter(
        visit=visit, is_completed=False,
    ).select_related("radiology_service")

    has_xray = any(
        r.radiology_service.service_type in ("XRAY", "MRI", "CT_SCAN", "OTHER")
        for r in pending
    )
    has_ultrasound = any(
        r.radiology_service.service_type == "ULTRASOUND"
        for r in pending
    )

    if has_xray:
        return Visit.Status.WAITING_XRAY
    if has_ultrasound:
        return Visit.Status.WAITING_ULTRASOUND
    return Visit.Status.WAITING_DOCTOR_REVIEW


# ─── Complete consultation (final action) ──────────────────────────

def complete_consultation(consultation_id, prescriptions_data=None,
                          request_admission=False, diagnosis="",
                          notes="", treatment_plan="", user=None):
    """
    Complete a consultation with prescriptions, admission, or just finish.
    """
    from triage.models import Visit
    from triage.services import log_visit_event
    from billing.services import get_or_create_visit_invoice, add_invoice_item

    with transaction.atomic():
        consultation = Consultation.objects.select_for_update().get(pk=consultation_id)
        visit = consultation.visit

        if consultation.status != Consultation.Status.IN_PROGRESS:
            raise ValueError("Consultation is not in progress.")

        consultation.diagnosis = diagnosis or consultation.diagnosis
        consultation.notes = notes or consultation.notes
        consultation.treatment_plan = treatment_plan
        consultation.status = Consultation.Status.COMPLETED
        consultation.completed_at = timezone.now()
        consultation.save(update_fields=[
            "diagnosis", "notes", "treatment_plan", "status",
            "completed_at", "updated_at",
        ])

        invoice = get_or_create_visit_invoice(visit, user)

        consult_item = None
        from core.models import Item
        consult_item = Item.objects.filter(
            category=Item.Category.CONSULTATION, is_active=True,
        ).first()

        add_invoice_item(
            invoice,
            description=f"Consultation Fee - Dr. {DOCTOR_NAME}",
            quantity=1,
            unit_price=consultation.consultation_fee,
            item=consult_item,
        )

        parts = []

        if prescriptions_data:
            _create_prescriptions(consultation, prescriptions_data)
            parts.append(f"{len(prescriptions_data)} prescription(s)")
            log_visit_event(
                visit, "Prescription Issued",
                f"{len(prescriptions_data)} medication(s) prescribed.",
                user=user,
            )

        if request_admission:
            visit.status = Visit.Status.ADMISSION_IN_PROGRESS
            visit.save(update_fields=["status", "updated_at"])
            parts.append("admission requested")
            log_visit_event(
                visit, "Admission Requested",
                "Doctor requested patient admission.",
                user=user,
            )
        elif prescriptions_data:
            visit.status = Visit.Status.WAITING_PHARMACY
            visit.save(update_fields=["status", "updated_at"])
        else:
            visit.status = Visit.Status.COMPLETED
            visit.save(update_fields=["status", "updated_at"])

        desc = f"Consultation completed. {', '.join(parts)}." if parts else "Consultation completed."
        log_visit_event(visit, "Consultation Completed", desc, user=user)

        return consultation


def cancel_consultation(consultation_id, user=None):
    """Cancel an in-progress consultation."""
    from triage.models import Visit
    from triage.services import log_visit_event

    with transaction.atomic():
        consultation = Consultation.objects.select_for_update().get(pk=consultation_id)
        visit = consultation.visit

        consultation.status = Consultation.Status.CANCELLED
        consultation.save(update_fields=["status", "updated_at"])

        if visit.status == Visit.Status.IN_CONSULTATION:
            visit.status = Visit.Status.WAITING_DOCTOR
            visit.save(update_fields=["status", "updated_at"])

        log_visit_event(visit, "Consultation Cancelled", user=user)

        return consultation


# ─── Prescriptions ─────────────────────────────────────────────────

def _create_prescriptions(consultation, prescriptions_data):
    """Create prescription records from form data."""
    for data in prescriptions_data:
        medicine_id = data.get("medicine_id")
        if not medicine_id:
            continue
        Prescription.objects.create(
            consultation=consultation,
            medicine_id=medicine_id,
            dosage=data.get("dosage", ""),
            dosage_unit=data.get("dosage_unit", Prescription.DosageUnit.MG),
            frequency=data.get("frequency", ""),
            duration_days=data.get("duration_days", 1),
            quantity=data.get("quantity", 1),
            route=data.get("route", "Oral"),
            instructions=data.get("instructions", ""),
        )


# ─── Return from diagnostic tests ─────────────────────────────────

def return_from_tests(visit, test_type, user=None):
    """
    Called when a diagnostic department completes all requests.
    Routes to the next test type or back to doctor review.
    """
    from triage.models import Visit
    from triage.services import log_visit_event

    next_status = _check_pending_test_queues(visit)

    if next_status:
        visit.status = next_status
        status_display = visit.get_status_display()
        visit.save(update_fields=["status", "updated_at"])
        log_visit_event(
            visit, f"{test_type} Completed",
            f"All {test_type.lower()} results ready. Routed to {status_display}.",
            user=user,
        )
    else:
        visit.status = Visit.Status.WAITING_DOCTOR_REVIEW
        visit.save(update_fields=["status", "updated_at"])
        log_visit_event(
            visit, f"{test_type} Completed",
            f"All {test_type.lower()} results ready. Returned to doctor for review.",
            user=user,
        )


def _check_pending_test_queues(visit):
    """Check if there are other pending test types for the visit."""
    from triage.models import Visit
    from laboratory.models import LabRequest
    from radiology.models import RadiologyRequest

    has_pending_lab = LabRequest.objects.filter(
        visit=visit, is_completed=False,
    ).exists()

    has_pending_xray = RadiologyRequest.objects.filter(
        visit=visit, is_completed=False,
        radiology_service__service_type__in=["XRAY", "MRI", "CT_SCAN", "OTHER"],
    ).exists()

    has_pending_ultrasound = RadiologyRequest.objects.filter(
        visit=visit, is_completed=False,
        radiology_service__service_type="ULTRASOUND",
    ).exists()

    if has_pending_lab:
        return Visit.Status.WAITING_LAB
    if has_pending_xray:
        return Visit.Status.WAITING_XRAY
    if has_pending_ultrasound:
        return Visit.Status.WAITING_ULTRASOUND
    return None
