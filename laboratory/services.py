"""
Service layer for laboratory app.
Only doctors create lab requests. Lab technicians only perform requested tests.
"""
from django.db import transaction
from django.utils import timezone

from .models import LabTest, LabRequest


def get_lab_queue():
    """Get all visits waiting for lab."""
    from triage.models import Visit
    return (
        Visit.objects
        .filter(status=Visit.Status.WAITING_LAB)
        .select_related("patient", "patient__patient_category")
        .order_by("created_at")
    )


def get_visit_lab_requests(visit_id):
    """Get visit with all lab requests."""
    from triage.models import Visit
    return (
        Visit.objects
        .select_related("patient", "patient__patient_category")
        .prefetch_related("lab_requests__lab_test", "triage_assessments")
        .get(pk=visit_id)
    )


def create_lab_request(visit_id, lab_test_id, clinical_indication="", priority="ROUTINE", user=None):
    """
    Create a lab request for a visit.
    Only called by doctors during consultation.
    """
    from triage.models import Visit
    from billing.services import get_or_create_visit_invoice, add_invoice_item
    from triage.services import log_visit_event

    with transaction.atomic():
        visit = Visit.objects.select_for_update().get(pk=visit_id)
        lab_test = LabTest.objects.get(pk=lab_test_id)

        request = LabRequest.objects.create(
            visit=visit,
            lab_test=lab_test,
            clinical_indication=clinical_indication,
            priority=priority,
            requested_by=user,
        )

        if visit.status != Visit.Status.WAITING_LAB:
            visit.status = Visit.Status.WAITING_LAB
            visit.save(update_fields=["status", "updated_at"])

        invoice = get_or_create_visit_invoice(visit, user)
        add_invoice_item(
            invoice,
            description=f"Lab: {lab_test.name}",
            quantity=1,
            unit_price=lab_test.price,
            item=lab_test.item,
        )

        log_visit_event(visit, "Lab Requested",
                        f"Lab test: {lab_test.name} ({priority})",
                        user=user)

        return request


def remove_lab_request(request_id):
    """Remove a lab request and adjust billing."""
    from billing.models import Invoice, InvoiceItem
    from triage.services import log_visit_event

    with transaction.atomic():
        lab_request = LabRequest.objects.select_related(
            "visit", "lab_test",
        ).get(pk=request_id)

        visit = lab_request.visit

        InvoiceItem.objects.filter(
            invoice__visit=visit,
            description=f"Lab: {lab_request.lab_test.name}",
        ).delete()

        invoice = Invoice.objects.filter(visit=visit).first()
        if invoice:
            total = sum(item.total_price for item in invoice.items.all())
            invoice.total_amount = total
            invoice.save(update_fields=["total_amount", "updated_at"])

        test_name = lab_request.lab_test.name
        lab_request.delete()

        log_visit_event(visit, "Lab Request Removed",
                        f"Removed lab test: {test_name}",
                        user=None)

        if not LabRequest.objects.filter(visit=visit, is_completed=False).exists():
            from triage.models import Visit as VisitModel
            if visit.status == VisitModel.Status.WAITING_LAB:
                visit.status = VisitModel.Status.WAITING_DOCTOR_REVIEW
                visit.save(update_fields=["status", "updated_at"])
                log_visit_event(visit, "Returned to Doctor",
                                "No pending lab tests. Patient returned to doctor.",
                                user=None)

        return visit


def complete_lab_request(request_id, result, remarks="", user=None):
    """Complete a single lab request with results."""
    with transaction.atomic():
        lab_request = LabRequest.objects.select_for_update().get(pk=request_id)
        lab_request.result = result
        lab_request.remarks = remarks
        lab_request.is_completed = True
        lab_request.completed_by = user
        lab_request.completed_at = timezone.now()
        lab_request.save(update_fields=[
            "result", "remarks", "is_completed",
            "completed_by", "completed_at", "updated_at",
        ])
        return lab_request


def save_draft_result(request_id, result, remarks=""):
    """Save result as draft without marking as completed."""
    with transaction.atomic():
        lab_request = LabRequest.objects.select_for_update().get(pk=request_id)
        lab_request.result = result
        lab_request.remarks = remarks
        lab_request.result_status = LabRequest.Status.DRAFT
        lab_request.save(update_fields=["result", "remarks", "result_status", "updated_at"])
        return lab_request


def save_all_draft_results(visit_id, results_data):
    """
    Save draft results for all lab requests in a visit.
    results_data: dict mapping request_id -> {result, remarks}
    """
    with transaction.atomic():
        for req_id, data in results_data.items():
            LabRequest.objects.filter(pk=req_id).update(
                result=data.get("result", ""),
                remarks=data.get("remarks", ""),
                result_status=LabRequest.Status.DRAFT,
            )


def finalize_results(visit_id, results_data, user=None):
    """
    Finalize all lab results (mark as FINAL) and complete all tests.
    Then send patient back to doctor for review.
    """
    from triage.models import Visit
    from triage.services import log_visit_event
    from consultation.services import return_from_tests

    with transaction.atomic():
        visit = Visit.objects.select_for_update().get(pk=visit_id)

        pending = LabRequest.objects.filter(visit=visit, is_completed=False)
        now = timezone.now()

        for req in pending:
            req_id = str(req.pk)
            if req_id in results_data:
                req.result = results_data[req_id].get("result", "")
                req.remarks = results_data[req_id].get("remarks", "")

            req.result_status = LabRequest.Status.FINAL
            req.is_completed = True
            req.completed_by = user
            req.completed_at = now
            req.save(update_fields=[
                "result", "remarks", "result_status", "is_completed",
                "completed_by", "completed_at", "updated_at",
            ])

        count = pending.count()

        return_from_tests(visit, "Lab", user=user)

        log_visit_event(visit, "Lab Results Complete",
                        f"All {count} lab test(s) completed. Sent for doctor review.",
                        user=user)

        return visit, count


def finalize_all_results(visit_id, user=None):
    """
    Finalize ALL lab results (both draft and pending) and send back to doctor.
    Marks all as FINAL and completes them.
    """
    from triage.models import Visit
    from triage.services import log_visit_event
    from consultation.services import return_from_tests

    with transaction.atomic():
        visit = Visit.objects.select_for_update().get(pk=visit_id)

        pending = LabRequest.objects.filter(visit=visit, is_completed=False)
        now = timezone.now()
        count = pending.update(
            result_status=LabRequest.Status.FINAL,
            is_completed=True,
            completed_by=user,
            completed_at=now,
        )

        return_from_tests(visit, "Lab", user=user)

        log_visit_event(visit, "Lab Results Complete",
                        f"All {count} lab test(s) completed. Sent for doctor review.",
                        user=user)

        return visit, count


def get_all_lab_requests_for_visit(visit_id):
    """Get all lab requests for a specific visit."""
    return LabRequest.objects.filter(
        visit_id=visit_id,
    ).select_related("lab_test", "completed_by", "requested_by").order_by("created_at")


def get_available_lab_tests():
    """Get all active lab tests."""
    return LabTest.objects.filter(is_active=True).order_by("category", "name")
