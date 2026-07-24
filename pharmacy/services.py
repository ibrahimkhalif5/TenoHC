"""
Service layer for pharmacy app.
"""
from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone

from .models import PharmacyDispense


def get_pharmacy_queue():
    """Get all visits waiting for pharmacy."""
    from triage.models import Visit
    return (
        Visit.objects
        .filter(status=Visit.Status.WAITING_PHARMACY)
        .select_related("patient", "patient__patient_category")
        .prefetch_related(
            "consultations__prescriptions__medicine",
            "consultations__doctor",
        )
        .order_by("created_at")
    )


def get_visit_for_dispensing(visit_id):
    """Get a visit with all data needed for dispensing view."""
    from triage.models import Visit
    return (
        Visit.objects
        .select_related("patient", "patient__patient_category")
        .prefetch_related(
            "consultations__prescriptions__medicine",
            "consultations__doctor",
            "pharmacy_dispenses__medicine",
            "pharmacy_dispenses__dispensed_by",
        )
        .get(pk=visit_id)
    )


def get_undispensed_prescriptions(visit_id):
    """Get all prescriptions for a visit that have not been dispensed."""
    from consultation.models import Prescription
    return Prescription.objects.filter(
        consultation__visit_id=visit_id,
        is_dispensed=False,
    ).select_related("medicine")


def get_dispense_history(visit_id):
    """Get dispensing history for a visit."""
    return PharmacyDispense.objects.filter(
        visit_id=visit_id,
    ).select_related("medicine", "dispensed_by").order_by("-dispensed_at")


def dispense_prescription(prescription_id, user):
    """
    Dispense a single prescription.
    Auto-bills at item master price. Auto-completes visit when all done.
    """
    from consultation.models import Prescription
    from billing.services import get_or_create_visit_invoice, add_invoice_item
    from triage.models import Visit
    from triage.services import log_visit_event

    with transaction.atomic():
        prescription = Prescription.objects.select_related(
            "consultation__visit", "medicine",
        ).select_for_update().get(pk=prescription_id)

        if prescription.is_dispensed:
            raise ValueError(f"{prescription.medicine.name} has already been dispensed.")

        visit = prescription.consultation.visit
        quantity_needed = float(prescription.quantity)

        unit_price = prescription.medicine.item.unit_price if prescription.medicine.item else prescription.medicine.selling_price
        total_charge = Decimal(str(quantity_needed)) * unit_price

        dispense = PharmacyDispense.objects.create(
            visit=visit,
            prescription=prescription,
            medicine=prescription.medicine,
            quantity_dispensed=prescription.quantity,
            batch_number="",
            charge=total_charge,
            notes=f"{prescription.dosage} {prescription.frequency}",
            dispensed_by=user,
        )

        prescription.is_dispensed = True
        prescription.save(update_fields=["is_dispensed", "updated_at"])

        invoice = get_or_create_visit_invoice(visit, user)
        add_invoice_item(
            invoice,
            description=f"{prescription.medicine.name} ({prescription.dosage} {prescription.frequency})",
            quantity=prescription.quantity,
            unit_price=unit_price,
        )

        pending = get_undispensed_prescriptions(visit.pk)
        if not pending.exists():
            visit.status = Visit.Status.COMPLETED
            visit.save(update_fields=["status", "updated_at"])
            log_visit_event(
                visit, "Visit Completed",
                "All prescriptions dispensed. Visit completed.",
                user=user,
            )

        return dispense


def dispense_all_pending(visit_id, user):
    """Dispense all pending prescriptions for a visit."""
    pending = get_undispensed_prescriptions(visit_id)
    if not pending.exists():
        raise ValueError("No pending prescriptions to dispense.")

    results = []
    for prescription in pending:
        results.append(dispense_prescription(prescription.pk, user))
    return results


def get_pharmacy_stats():
    """Get pharmacy dashboard statistics."""
    today = timezone.now().date()
    total_dispensed_today = PharmacyDispense.objects.filter(
        dispensed_at__date=today,
    ).count()
    total_charge_today = PharmacyDispense.objects.filter(
        dispensed_at__date=today,
    ).aggregate(total=models.Sum("charge"))["total"] or 0

    pending_count = get_undispensed_prescriptions_for_all_visits().count()

    return {
        "total_dispensed_today": total_dispensed_today,
        "total_charge_today": total_charge_today,
        "pending_count": pending_count,
    }


def get_undispensed_prescriptions_for_all_visits():
    """Get all undispensed prescriptions across all visits."""
    from consultation.models import Prescription
    return Prescription.objects.filter(
        is_dispensed=False,
    ).select_related(
        "consultation__visit__patient",
        "medicine",
    )


def finish_visit(visit_id, user=None):
    """Explicitly mark a visit as completed after all prescriptions are dispensed."""
    from triage.models import Visit
    from triage.services import log_visit_event

    with transaction.atomic():
        visit = Visit.objects.select_for_update().get(pk=visit_id)
        if visit.status != Visit.Status.WAITING_PHARMACY:
            raise ValueError("Patient is not in the pharmacy queue.")

        pending = get_undispensed_prescriptions(visit_id)
        if pending.exists():
            raise ValueError("There are still undispensed prescriptions. Please dispense all before finishing.")

        visit.status = Visit.Status.COMPLETED
        visit.save(update_fields=["status", "updated_at"])
        log_visit_event(visit, "Visit Completed", "All prescriptions dispensed. Visit marked as completed.", user=user)
        return visit
