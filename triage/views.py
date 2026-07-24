from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from .models import Visit
from .forms import TriageAssessmentForm
from . import services


class TriageQueueView(LoginRequiredMixin, View):
    """Display patients waiting for triage."""

    def get(self, request):
        queue = services.get_triage_queue()
        return render(request, "triage/queue.html", {
            "visits": queue,
            "queue_count": queue.count(),
        })


class TriageAssessView(LoginRequiredMixin, View):
    """Triage assessment: view patient info + capture vitals."""

    def get(self, request, visit_id):
        visit = services.get_visit(visit_id)
        if visit.status != Visit.Status.WAITING_TRIAGE:
            messages.warning(request, "This patient is not waiting for triage.")
            return redirect("triage:triage-list")
        form = TriageAssessmentForm()
        return render(request, "triage/assess.html", {
            "visit": visit,
            "patient": visit.patient,
            "form": form,
        })

    def post(self, request, visit_id):
        visit = services.get_visit(visit_id)
        if visit.status != Visit.Status.WAITING_TRIAGE:
            messages.warning(request, "This patient is not waiting for triage.")
            return redirect("triage:triage-list")
        form = TriageAssessmentForm(request.POST)
        if form.is_valid():
            assessment = services.complete_triage(
                visit_id=visit.pk,
                form_data=form.cleaned_data,
                user=request.user,
            )
            messages.success(
                request,
                f"Triage completed for {visit.patient.full_name}. "
                f"Patient {visit.patient.patient_number} has been released to doctor.",
            )
            return redirect("triage:triage-list")
        return render(request, "triage/assess.html", {
            "visit": visit,
            "patient": visit.patient,
            "form": form,
        })
