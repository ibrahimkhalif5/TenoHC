from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from triage.models import Visit
from .models import RadiologyRequest, RadiologyService
from . import services


class RadiologyQueueView(LoginRequiredMixin, View):
    """Display patients waiting for radiology (X-ray, Ultrasound, etc.)."""

    def get(self, request):
        queue = services.get_radiology_queue()
        return render(request, "radiology/queue.html", {
            "visits": queue,
            "queue_count": queue.count(),
        })


class RadiologyVisitDetailView(LoginRequiredMixin, View):
    """
    View doctor-requested radiology services and enter findings.
    The radiographer NEVER creates requests - only doctors do.
    """

    def get(self, request, visit_id):
        visit = (
            Visit.objects
            .select_related("patient", "patient__patient_category")
            .prefetch_related("radiology_requests__radiology_service", "triage_assessments")
            .get(pk=visit_id)
        )
        radiology_requests = (
            RadiologyRequest.objects
            .filter(visit_id=visit_id)
            .select_related("radiology_service", "completed_by", "requested_by")
            .order_by("created_at")
        )
        pending_count = radiology_requests.filter(is_completed=False).count()
        completed_count = radiology_requests.filter(is_completed=True).count()

        # Get the requesting doctor
        requesting_doctor = None
        clinical_indication = ""
        first_request = radiology_requests.first()
        if first_request and first_request.requested_by:
            requesting_doctor = first_request.requested_by
        if first_request and first_request.clinical_indication:
            clinical_indication = first_request.clinical_indication

        return render(request, "radiology/detail.html", {
            "visit": visit,
            "patient": visit.patient,
            "radiology_requests": radiology_requests,
            "pending_count": pending_count,
            "completed_count": completed_count,
            "requesting_doctor": requesting_doctor,
            "clinical_indication": clinical_indication,
        })


class RadiologySaveDraftView(LoginRequiredMixin, View):
    """Save draft findings without marking requests as completed."""

    def post(self, request, visit_id):
        results_data = {}
        for key, value in request.POST.items():
            if key.startswith("findings_"):
                req_id = key.replace("findings_", "")
                impression_key = f"impression_{req_id}"
                impression = request.POST.get(impression_key, "").strip()
                results_data[req_id] = {
                    "findings": value.strip(),
                    "impression": impression,
                }

        services.save_all_draft_findings(visit_id, results_data)
        messages.success(request, "Draft saved successfully.")
        return redirect("radiology:radiology-detail", visit_id=visit_id)


class RadiologySubmitResultView(LoginRequiredMixin, View):
    """Submit findings for a single radiology request."""

    def post(self, request, visit_id, request_id):
        findings = request.POST.get("findings", "").strip()
        impression = request.POST.get("impression", "").strip()
        image = request.FILES.get("image")

        if not findings:
            messages.error(request, "Findings are required.")
            return redirect("radiology:radiology-detail", visit_id=visit_id)

        services.complete_radiology_request(
            request_id=request_id,
            findings=findings,
            impression=impression,
            image=image,
            user=request.user,
        )
        messages.success(request, "Radiology report submitted successfully.")
        return redirect("radiology:radiology-detail", visit_id=visit_id)


class RadiologyFinalizeResultsView(LoginRequiredMixin, View):
    """Finalize all results and send back to doctor for review."""

    def post(self, request, visit_id):
        results_data = {}
        for key, value in request.POST.items():
            if key.startswith("findings_"):
                req_id = key.replace("findings_", "")
                impression_key = f"impression_{req_id}"
                impression = request.POST.get(impression_key, "").strip()
                results_data[req_id] = {
                    "findings": value.strip(),
                    "impression": impression,
                }

        visit, count = services.finalize_radiology_results(
            visit_id=visit_id,
            results_data=results_data,
            user=request.user,
        )
        messages.success(
            request,
            f"All {count} imaging report(s) finalized. Patient sent back to doctor for review.",
        )
        return redirect("radiology:radiology-list")


class RadiologyCompleteAllView(LoginRequiredMixin, View):
    """Complete all pending radiology requests and send back to doctor."""

    def post(self, request, visit_id):
        visit, count = services.finalize_all_radiology_requests(
            visit_id=visit_id, user=request.user,
        )
        messages.success(
            request,
            f"All {count} imaging request(s) completed. Patient sent back to doctor for review.",
        )
        return redirect("radiology:radiology-list")
