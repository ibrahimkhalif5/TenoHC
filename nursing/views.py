from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View

from .forms import NursingNoteForm, DailyVitalsForm, TreatmentForm
from . import services


class PatientListView(LoginRequiredMixin, View):
    """List all admitted patients."""

    def get(self, request):
        admitted = services.get_admitted_patients()
        return render(request, "nursing/patient_list.html", {
            "admitted_patients": admitted,
            "count": admitted.count(),
        })


class PatientDetailView(LoginRequiredMixin, View):
    """View a patient's nursing record: vitals, notes, treatments."""

    def get(self, request, admission_id):
        admission = services.get_admission_detail(admission_id)
        return render(request, "nursing/patient_detail.html", {
            "admission": admission,
            "patient": admission.patient,
            "note_form": NursingNoteForm(),
            "vitals_form": DailyVitalsForm(),
            "treatment_form": TreatmentForm(),
        })


class AddNursingNoteView(LoginRequiredMixin, View):
    def post(self, request, admission_id):
        form = NursingNoteForm(request.POST)
        if form.is_valid():
            services.add_nursing_note(admission_id, form.cleaned_data["note"], request.user)
            messages.success(request, "Nursing note added.")
        else:
            messages.error(request, "Failed to add note.")
        return redirect("nursing:nursing-detail", admission_id=admission_id)


class AddDailyVitalsView(LoginRequiredMixin, View):
    def post(self, request, admission_id):
        form = DailyVitalsForm(request.POST)
        if form.is_valid():
            services.add_daily_vitals(admission_id, form.cleaned_data, request.user)
            messages.success(request, "Daily vitals recorded.")
        else:
            messages.error(request, "Failed to record vitals.")
        return redirect("nursing:nursing-detail", admission_id=admission_id)


class AddTreatmentView(LoginRequiredMixin, View):
    def post(self, request, admission_id):
        form = TreatmentForm(request.POST)
        if form.is_valid():
            services.add_treatment(admission_id, form.cleaned_data, request.user)
            messages.success(request, "Treatment recorded.")
        else:
            messages.error(request, "Failed to record treatment.")
        return redirect("nursing:nursing-detail", admission_id=admission_id)
