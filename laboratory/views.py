from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import HttpResponse

from triage.models import Visit
from .models import LabRequest, LabTest, LabTestTemplate, LabTestParameter, LabTestResultValue
from . import services


class LabQueueView(LoginRequiredMixin, View):
    """Display patients waiting for lab + recent completed reports."""

    def get(self, request):
        queue = services.get_lab_queue()

        completed_visits = (
            Visit.objects
            .filter(lab_requests__is_completed=True)
            .distinct()
            .select_related("patient")
            .prefetch_related("lab_requests__lab_test")
            .order_by("-updated_at")[:20]
        )

        return render(request, "laboratory/queue.html", {
            "visits": queue,
            "queue_count": queue.count(),
            "completed_visits": completed_visits,
        })


class LabVisitDetailView(LoginRequiredMixin, View):
    """
    Lab worklist: shows doctor-requested tests and lets technician enter results.
    The technician NEVER creates requests - only doctors do.
    """

    def get(self, request, visit_id):
        visit = (
            Visit.objects
            .select_related("patient", "patient__patient_category")
            .prefetch_related("lab_requests__lab_test", "triage_assessments")
            .get(pk=visit_id)
        )

        lab_requests = (
            LabRequest.objects
            .filter(visit_id=visit_id)
            .select_related("lab_test", "completed_by", "requested_by")
            .order_by("created_at")
        )

        pending_count = lab_requests.filter(is_completed=False).count()
        completed_count = lab_requests.filter(is_completed=True).count()
        all_completed = pending_count == 0 and lab_requests.count() > 0

        requesting_doctor = None
        first_request = lab_requests.first()
        if first_request and first_request.requested_by:
            requesting_doctor = first_request.requested_by

        clinical_indication = ""
        if first_request and first_request.clinical_indication:
            clinical_indication = first_request.clinical_indication

        # Build template data for each request
        request_data = []
        for req in lab_requests:
            template = LabTestTemplate.objects.filter(lab_test=req.lab_test).first()
            parameters = []
            result_values = {}
            if template:
                parameters = list(template.parameters.order_by("display_order", "name"))
                result_values = dict(
                    LabTestResultValue.objects
                    .filter(lab_request=req)
                    .values_list("parameter_id", "value")
                )
            request_data.append({
                "req": req,
                "template": template,
                "parameters": parameters,
                "result_values": result_values,
            })

        return render(request, "laboratory/detail.html", {
            "visit": visit,
            "patient": visit.patient,
            "lab_requests": lab_requests,
            "request_data": request_data,
            "pending_count": pending_count,
            "completed_count": completed_count,
            "total_count": lab_requests.count(),
            "all_completed": all_completed,
            "requesting_doctor": requesting_doctor,
            "clinical_indication": clinical_indication,
            "hospital": _get_hospital_settings(),
        })


class LabSaveDraftView(LoginRequiredMixin, View):
    """Save draft results without marking tests as completed."""

    def post(self, request, visit_id):
        results_data = {}
        for key, value in request.POST.items():
            if key.startswith("result_"):
                req_id = key.replace("result_", "")
                remarks_key = f"remarks_{req_id}"
                remarks = request.POST.get(remarks_key, "").strip()
                results_data[req_id] = {
                    "result": value.strip(),
                    "remarks": remarks,
                }

        services.save_all_draft_results(visit_id, results_data)
        _save_structured_results(request)
        messages.success(request, "Draft saved successfully.")
        return redirect("laboratory:lab-detail", visit_id=visit_id)


class LabFinalizeResultsView(LoginRequiredMixin, View):
    """Finalize all results and send back to doctor for review."""

    def post(self, request, visit_id):
        results_data = {}
        for key, value in request.POST.items():
            if key.startswith("result_"):
                req_id = key.replace("result_", "")
                remarks_key = f"remarks_{req_id}"
                remarks = request.POST.get(remarks_key, "").strip()
                results_data[req_id] = {
                    "result": value.strip(),
                    "remarks": remarks,
                }

        _save_structured_results(request)
        visit, count = services.finalize_results(
            visit_id=visit_id,
            results_data=results_data,
            user=request.user,
        )
        messages.success(
            request,
            f"All {count} lab test(s) finalized. Patient sent back to doctor for review.",
        )
        return redirect("laboratory:lab-list")


class LabCompleteAllView(LoginRequiredMixin, View):
    """Complete all pending lab requests and send back to doctor."""

    def post(self, request, visit_id):
        visit, count = services.finalize_all_results(
            visit_id=visit_id, user=request.user,
        )
        messages.success(
            request,
            f"All {count} lab test(s) completed. Patient sent back to doctor for review.",
        )
        return redirect("laboratory:lab-list")


class LabReportPDFView(LoginRequiredMixin, View):
    """Generate and download a PDF lab report."""

    def get(self, request, visit_id):
        from .pdf_generator import generate_lab_report_pdf
        buffer = generate_lab_report_pdf(visit_id)
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="lab-report-{visit_id}.pdf"'
        return response


class LabReportPrintView(LoginRequiredMixin, View):
    """Open printable lab report in new tab."""

    def get(self, request, visit_id):
        from .pdf_generator import generate_lab_report_pdf
        buffer = generate_lab_report_pdf(visit_id)
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="lab-report-{visit_id}.pdf"'
        return response


def _get_hospital_settings():
    from core.models import HospitalSetting
    return HospitalSetting.load()


def _save_structured_results(request):
    """Save structured parameter results from POST data.
    POST keys: param_<lab_request_id>_<parameter_id> = value"""
    from django.db.models import Q

    save_map = {}  # {lab_request_id: {parameter_id: value}}
    for key, value in request.POST.items():
        if key.startswith("param_"):
            parts = key.split("_")
            if len(parts) == 3:
                try:
                    req_id = int(parts[1])
                    param_id = int(parts[2])
                    if req_id not in save_map:
                        save_map[req_id] = {}
                    save_map[req_id][param_id] = value.strip()
                except (ValueError, TypeError):
                    continue

    for req_id, params in save_map.items():
        for param_id, value in params.items():
            LabTestResultValue.objects.update_or_create(
                lab_request_id=req_id,
                parameter_id=param_id,
                defaults={"value": value},
            )
