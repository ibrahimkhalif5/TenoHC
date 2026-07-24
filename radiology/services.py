"""
Service layer for radiology app.
Only doctors create radiology requests. Radiographers only perform requested imaging.
"""
from django.db import transaction
from django.utils import timezone

from .models import RadiologyService, RadiologyRequest


def get_radiology_queue():
    """Get all visits waiting for radiology (X-ray, Ultrasound, etc.)."""
    from triage.models import Visit
    return (
        Visit.objects
        .filter(status__in=[
            Visit.Status.WAITING_XRAY,
            Visit.Status.WAITING_ULTRASOUND,
        ])
        .select_related("patient", "patient__patient_category")
        .order_by("created_at")
    )


def get_visit_radiology_requests(visit_id):
    """Get visit with all radiology requests."""
    from triage.models import Visit
    return (
        Visit.objects
        .select_related("patient", "patient__patient_category")
        .prefetch_related("radiology_requests__radiology_service", "triage_assessments")
        .get(pk=visit_id)
    )


def create_radiology_request(visit_id, service_id, clinical_indication="", priority="ROUTINE", user=None):
    """
    Create a radiology request for a visit.
    Routes to WAITING_XRAY or WAITING_ULTRASOUND based on service type.
    Auto-bills the service.
    Only called by doctors during consultation.
    """
    from triage.models import Visit
    from billing.services import get_or_create_visit_invoice, add_invoice_item
    from triage.services import log_visit_event

    with transaction.atomic():
        visit = Visit.objects.select_for_update().get(pk=visit_id)
        service = RadiologyService.objects.get(pk=service_id)

        request = RadiologyRequest.objects.create(
            visit=visit,
            radiology_service=service,
            clinical_indication=clinical_indication,
            priority=priority,
            requested_by=user,
        )

        if service.service_type == "ULTRASOUND":
            target_status = Visit.Status.WAITING_ULTRASOUND
        else:
            target_status = Visit.Status.WAITING_XRAY

        if visit.status != target_status:
            visit.status = target_status
            visit.save(update_fields=["status", "updated_at"])

        invoice = get_or_create_visit_invoice(visit, user)
        add_invoice_item(
            invoice,
            description=f"Radiology: {service.name}",
            quantity=1,
            unit_price=service.price,
            item=service.item,
        )

        log_visit_event(visit, "Radiology Requested",
                        f"{service.get_service_type_display()}: {service.name} ({priority})",
                        user=user)

        return request


def remove_radiology_request(request_id):
    """Remove a radiology request and adjust billing."""
    from billing.models import Invoice, InvoiceItem
    from triage.services import log_visit_event

    with transaction.atomic():
        radiology_request = RadiologyRequest.objects.select_related(
            "visit", "radiology_service",
        ).get(pk=request_id)

        visit = radiology_request.visit

        InvoiceItem.objects.filter(
            invoice__visit=visit,
            description=f"Radiology: {radiology_request.radiology_service.name}",
        ).delete()

        invoice = Invoice.objects.filter(visit=visit).first()
        if invoice:
            total = sum(item.total_price for item in invoice.items.all())
            invoice.total_amount = total
            invoice.save(update_fields=["total_amount", "updated_at"])

        service_name = radiology_request.radiology_service.name
        radiology_request.delete()

        log_visit_event(visit, "Radiology Request Removed",
                        f"Removed imaging request: {service_name}",
                        user=None)

        if not RadiologyRequest.objects.filter(visit=visit, is_completed=False).exists():
            from triage.models import Visit as VisitModel
            if visit.status in (
                VisitModel.Status.WAITING_XRAY,
                VisitModel.Status.WAITING_ULTRASOUND,
            ):
                visit.status = VisitModel.Status.WAITING_DOCTOR_REVIEW
                visit.save(update_fields=["status", "updated_at"])
                log_visit_event(visit, "Returned to Doctor",
                                "No pending imaging. Patient returned to doctor.",
                                user=None)

        return visit


def complete_radiology_request(request_id, findings, impression="", image=None, user=None):
    """Complete a single radiology request with findings and impression."""
    with transaction.atomic():
        radiology_request = RadiologyRequest.objects.select_for_update().get(pk=request_id)
        radiology_request.findings = findings
        radiology_request.impression = impression
        radiology_request.is_completed = True
        radiology_request.completed_by = user
        radiology_request.completed_at = timezone.now()
        if image:
            radiology_request.image = image
        radiology_request.save(update_fields=[
            "findings", "impression", "is_completed", "image",
            "completed_by", "completed_at", "updated_at",
        ])
        return radiology_request


def save_draft_findings(request_id, findings, impression="", image=None):
    """Save findings as draft without marking as completed."""
    with transaction.atomic():
        radiology_request = RadiologyRequest.objects.select_for_update().get(pk=request_id)
        radiology_request.findings = findings
        radiology_request.impression = impression
        radiology_request.result_status = RadiologyRequest.Status.DRAFT
        if image:
            radiology_request.image = image
        radiology_request.save(update_fields=[
            "findings", "impression", "result_status", "image", "updated_at",
        ])
        return radiology_request


def save_all_draft_findings(visit_id, results_data):
    """
    Save draft findings for all radiology requests in a visit.
    results_data: dict mapping request_id -> {findings, impression}
    """
    with transaction.atomic():
        for req_id, data in results_data.items():
            RadiologyRequest.objects.filter(pk=req_id).update(
                findings=data.get("findings", ""),
                impression=data.get("impression", ""),
                result_status=RadiologyRequest.Status.DRAFT,
            )


def finalize_radiology_results(visit_id, results_data, user=None):
    """
    Finalize all radiology results (mark as FINAL) and send back to doctor.
    """
    from triage.models import Visit
    from triage.services import log_visit_event
    from consultation.services import return_from_tests

    with transaction.atomic():
        visit = Visit.objects.select_for_update().get(pk=visit_id)

        pending = RadiologyRequest.objects.filter(visit=visit, is_completed=False)
        now = timezone.now()

        for req in pending:
            req_id = str(req.pk)
            if req_id in results_data:
                req.findings = results_data[req_id].get("findings", "")
                req.impression = results_data[req_id].get("impression", "")

            req.result_status = RadiologyRequest.Status.FINAL
            req.is_completed = True
            req.completed_by = user
            req.completed_at = now
            req.save(update_fields=[
                "findings", "impression", "result_status", "is_completed",
                "completed_by", "completed_at", "updated_at",
            ])

        count = pending.count()

        return_from_tests(visit, "Radiology", user=user)

        log_visit_event(visit, "Radiology Results Complete",
                        f"All {count} imaging request(s) completed. Sent for doctor review.",
                        user=user)

        return visit, count


def finalize_all_radiology_requests(visit_id, user=None):
    """
    Finalize ALL radiology results and send back to doctor.
    Marks all as FINAL and completes them.
    """
    from triage.models import Visit
    from triage.services import log_visit_event
    from consultation.services import return_from_tests

    with transaction.atomic():
        visit = Visit.objects.select_for_update().get(pk=visit_id)

        pending = RadiologyRequest.objects.filter(visit=visit, is_completed=False)
        now = timezone.now()
        count = pending.update(
            result_status=RadiologyRequest.Status.FINAL,
            is_completed=True,
            completed_by=user,
            completed_at=now,
        )

        return_from_tests(visit, "Radiology", user=user)

        log_visit_event(visit, "Radiology Results Complete",
                        f"All {count} imaging request(s) completed. Sent for doctor review.",
                        user=user)

        return visit, count


def get_all_radiology_requests_for_visit(visit_id):
    """Get all radiology requests for a specific visit."""
    return RadiologyRequest.objects.filter(
        visit_id=visit_id,
    ).select_related("radiology_service", "completed_by", "requested_by").order_by("created_at")


def get_available_services():
    """Get all active radiology services."""
    return RadiologyService.objects.filter(is_active=True).order_by("service_type", "name")
