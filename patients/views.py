import json
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from .models import Patient
from .forms import PatientRegistrationForm, PatientSearchForm, PatientUpdateForm
from . import services


class PatientRegisterView(LoginRequiredMixin, View):
    """Register a new patient or create a returning visit."""

    def get(self, request):
        form = PatientRegistrationForm()
        search_form = PatientSearchForm()
        search_results = []
        query = request.GET.get("q", "")
        if query:
            search_results = services.search_patients(query)
        return render(request, "patients/register.html", {
            "form": form,
            "search_form": search_form,
            "search_results": search_results,
            "query": query,
        })

    def post(self, request):
        form = PatientRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            patient = services.register_patient(form.cleaned_data, user=request.user)
            messages.success(
                request,
                f"Patient {patient.patient_number} ({patient.full_name}) registered successfully.",
            )
            return redirect("patients:patient-detail", pk=patient.pk)
        search_form = PatientSearchForm()
        return render(request, "patients/register.html", {
            "form": form,
            "search_form": search_form,
            "search_results": [],
            "query": "",
        })


class PatientListView(LoginRequiredMixin, View):
    """List all patients with search and pagination."""

    def get(self, request):
        form = PatientSearchForm(request.GET)
        queryset = Patient.objects.filter(is_active=True).order_by("-created_at")
        query = form.cleaned_data.get("query", "") if form.is_valid() else ""
        if query:
            queryset = services.search_patients(query).order_by("-created_at")
            paginator = Paginator(queryset, 20)
        else:
            paginator = Paginator(queryset, 20)
        page = request.GET.get("page")
        patients = paginator.get_page(page)
        return render(request, "patients/patient_list.html", {
            "patients": patients,
            "form": form,
            "query": query,
        })


class PatientDetailView(LoginRequiredMixin, View):
    """Patient profile with visit history, consultations, and more."""

    def get(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        visits = patient.visits.select_related("created_by").order_by("-created_at")[:20]
        invoices = (
            patient.invoices
            .select_related("visit", "created_by")
            .prefetch_related("items")
            .order_by("-created_at")[:20]
        )
        consultations = (
            patient.visits.prefetch_related(
                "consultations__prescriptions__medicine",
                "consultations__doctor",
            )
        )
        # Flatten: get all consultations across all visits
        consultation_list = []
        for v in consultations:
            for c in v.consultations.all():
                consultation_list.append(c)
        consultation_list.sort(key=lambda c: c.started_at, reverse=True)
        consultation_list = consultation_list[:20]

        lab_requests = (
            patient.visits.prefetch_related("lab_requests__lab_test", "lab_requests__completed_by", "lab_requests__requested_by")
        )
        lab_list = []
        for v in lab_requests:
            for r in v.lab_requests.all():
                lab_list.append(r)
        lab_list.sort(key=lambda r: r.created_at, reverse=True)
        lab_list = lab_list[:20]

        radiology_requests = (
            patient.visits.prefetch_related("radiology_requests__radiology_service", "radiology_requests__completed_by")
        )
        radiology_list = []
        for v in radiology_requests:
            for r in v.radiology_requests.all():
                radiology_list.append(r)
        radiology_list.sort(key=lambda r: r.created_at, reverse=True)
        radiology_list = radiology_list[:20]

        pharmacy_dispenses = (
            patient.visits.prefetch_related("pharmacy_dispenses__medicine", "pharmacy_dispenses__dispensed_by")
        )
        dispense_list = []
        for v in pharmacy_dispenses:
            for d in v.pharmacy_dispenses.all():
                dispense_list.append(d)
        dispense_list.sort(key=lambda d: d.dispensed_at, reverse=True)
        dispense_list = dispense_list[:20]

        return render(request, "patients/patient_detail.html", {
            "patient": patient,
            "visits": visits,
            "invoices": invoices,
            "consultations": consultation_list,
            "lab_requests": lab_list,
            "radiology_requests": radiology_list,
            "pharmacy_dispenses": dispense_list,
        })


class PatientSearchAPIView(LoginRequiredMixin, View):
    """JSON endpoint for AJAX patient search."""

    def get(self, request):
        q = request.GET.get("q", "")
        patients = services.search_patients(q)
        data = [
            {
                "id": p.id,
                "patient_number": p.patient_number,
                "full_name": p.full_name,
                "phone": p.phone,
                "gender": p.gender,
                "age": p.age,
            }
            for p in patients
        ]
        return JsonResponse(data, safe=False)


class PatientCreateVisitView(LoginRequiredMixin, View):
    """Create a new visit for an existing patient (returning visit)."""

    def post(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        visit = services.create_returning_visit(patient, user=request.user)
        messages.success(
            request,
            f"New visit {visit.visit_number} created for {patient.full_name}. Patient is now in triage queue.",
        )
        return redirect("triage:triage-list")


class PatientUpdateView(LoginRequiredMixin, View):
    """Edit an existing patient's details."""

    def get(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        form = PatientUpdateForm(instance=patient)
        return render(request, "patients/patient_edit.html", {
            "form": form,
            "patient": patient,
        })

    def post(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        form = PatientUpdateForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f"Patient {patient.full_name} updated successfully.")
            return redirect("patients:patient-detail", pk=patient.pk)
        return render(request, "patients/patient_edit.html", {
            "form": form,
            "patient": patient,
        })
