from datetime import date
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from django.http import HttpResponse, JsonResponse

from .models import DischargeSummary, DischargeMedication
from .forms import DischargeSummaryForm, DischargeMedicationForm, DoctorSignatureForm
from . import services
from billing.services import get_admission_billing_summary


class DischargeSummaryListView(LoginRequiredMixin, View):
    """List all discharge summaries - admin/doctor view."""

    def get(self, request):
        summaries = services.get_all_discharge_summaries()
        return render(request, "discharge/list.html", {
            "summaries": summaries,
        })


class DischargeSummaryCreateView(LoginRequiredMixin, View):
    """Create or open existing discharge summary for an admission."""

    def get(self, request, admission_id):
        from admission.models import Admission
        admission = get_object_or_404(
            Admission.objects.select_related(
                "patient", "ward", "room", "bed", "visit",
            ),
            pk=admission_id,
        )

        summary = services.get_discharge_summary(admission_id)
        if not summary:
            summary = services.create_discharge_summary(
                admission_id=admission_id, user=request.user,
            )

        # Auto-populate all empty fields from clinical data
        services.auto_populate_summary(summary)

        form = DischargeSummaryForm(instance=summary)
        med_form = DischargeMedicationForm()
        sig_form = DoctorSignatureForm()

        # Auto-populate clinical info from existing records
        labs, rads = services.get_investigations_for_visit(admission.visit)
        treatments = services.get_treatments_for_admission(admission)
        billing = get_admission_billing_summary(admission)

        return render(request, "discharge/create.html", {
            "admission": admission,
            "summary": summary,
            "form": form,
            "med_form": med_form,
            "sig_form": sig_form,
            "labs": labs,
            "rads": rads,
            "treatments": treatments,
            "billing": billing,
        })


class DischargeSummarySaveView(LoginRequiredMixin, View):
    """Save discharge summary draft."""

    def post(self, request, summary_id):
        summary = get_object_or_404(DischargeSummary, pk=summary_id)

        if summary.status == DischargeSummary.Status.FINALIZED:
            messages.warning(request, "Cannot edit a finalized discharge summary.")
            if request.headers.get("HX-Request"):
                return HttpResponse("")
            return redirect("discharge:discharge-summary-detail", summary_id=summary.pk)

        data = request.POST.copy()
        if request.FILES.get("doctor_signature"):
            data["doctor_signature"] = request.FILES["doctor_signature"]

        summary = services.save_draft(summary_id, data, user=request.user)

        if request.headers.get("HX-Request"):
            return HttpResponse("Saved")

        messages.success(request, "Discharge summary saved successfully.")
        return redirect("discharge:discharge-summary-detail", summary_id=summary.pk)


class DischargeSummaryDetailView(LoginRequiredMixin, View):
    """View a discharge summary."""

    def get(self, request, summary_id):
        summary = get_object_or_404(
            DischargeSummary.objects.select_related(
                "admission",
                "admission__patient",
                "admission__ward",
                "admission__room",
                "admission__bed",
                "admission__visit",
                "created_by",
                "finalized_by",
            ),
            pk=summary_id,
        )

        admission = summary.admission
        form = DischargeSummaryForm(instance=summary)
        med_form = DischargeMedicationForm()
        sig_form = DoctorSignatureForm()

        labs, rads = services.get_investigations_for_visit(admission.visit)
        treatments = services.get_treatments_for_admission(admission)
        billing = get_admission_billing_summary(admission)

        return render(request, "discharge/detail.html", {
            "admission": admission,
            "summary": summary,
            "form": form,
            "med_form": med_form,
            "sig_form": sig_form,
            "labs": labs,
            "rads": rads,
            "treatments": treatments,
            "billing": billing,
        })


class DischargeSummaryFinalizeView(LoginRequiredMixin, View):
    """Finalize the discharge summary and discharge the patient."""

    def post(self, request, summary_id):
        summary = get_object_or_404(DischargeSummary, pk=summary_id)

        if summary.status == DischargeSummary.Status.FINALIZED:
            messages.warning(request, "Discharge summary is already finalized.")
            return redirect("discharge:discharge-summary-detail", summary_id=summary.pk)

        # Save any unsaved fields first
        data = request.POST.copy()
        if request.FILES.get("doctor_signature"):
            data["doctor_signature"] = request.FILES["doctor_signature"]
        services.save_draft(summary_id, data, user=request.user)

        # Re-fetch after save
        summary = get_object_or_404(DischargeSummary, pk=summary_id)

        summary, errors = services.finalize_discharge_summary(
            summary_id=summary_id, user=request.user,
        )

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("discharge:discharge-summary-detail", summary_id=summary.pk)

        messages.success(
            request,
            f"Discharge summary finalized and patient discharged successfully.",
        )
        return redirect("discharge:discharge-summary-detail", summary_id=summary.pk)


class DischargeMedicationAddView(LoginRequiredMixin, View):
    """Add a discharge medication."""

    def post(self, request, summary_id):
        summary = get_object_or_404(DischargeSummary, pk=summary_id)

        if summary.status == DischargeSummary.Status.FINALIZED:
            messages.warning(request, "Cannot edit a finalized discharge summary.")
            if request.headers.get("HX-Request"):
                return HttpResponse("")
            return redirect("discharge:discharge-summary-detail", summary_id=summary.pk)

        form = DischargeMedicationForm(request.POST)
        if form.is_valid():
            services.add_discharge_medication(summary_id, form.cleaned_data)
        else:
            messages.error(request, "Invalid medication data.")

        if request.headers.get("HX-Request"):
            summary.refresh_from_db()
            return render(request, "discharge/_medications_table.html", {
                "summary": summary,
            })

        return redirect("discharge:discharge-summary-detail", summary_id=summary.pk)


class DischargeMedicationRemoveView(LoginRequiredMixin, View):
    """Remove a discharge medication."""

    def post(self, request, med_id):
        med = get_object_or_404(DischargeMedication, pk=med_id)
        summary = med.discharge_summary
        summary_id = summary.pk

        if summary.status == DischargeSummary.Status.FINALIZED:
            messages.warning(request, "Cannot edit a finalized discharge summary.")
            if request.headers.get("HX-Request"):
                return HttpResponse("")
            return redirect("discharge:discharge-summary-detail", summary_id=summary_id)

        services.remove_discharge_medication(med_id)

        if request.headers.get("HX-Request"):
            summary.refresh_from_db()
            return render(request, "discharge/_medications_table.html", {
                "summary": summary,
            })

        return redirect("discharge:discharge-summary-detail", summary_id=summary_id)


class DischargeSummaryPDFView(LoginRequiredMixin, View):
    """Generate and download the discharge summary PDF."""

    def get(self, request, summary_id):
        from .pdf_generator import generate_discharge_pdf

        summary = get_object_or_404(
            DischargeSummary.objects.select_related(
                "admission",
                "admission__patient",
                "admission__ward",
                "admission__room",
                "admission__bed",
                "admission__visit",
                "created_by",
                "finalized_by",
            ),
            pk=summary_id,
        )

        pdf_buffer = generate_discharge_pdf(summary)

        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        patient_num = summary.admission.patient.patient_number
        filename = f"Discharge_Summary_{patient_num}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response


class DischargeSummaryPrintView(LoginRequiredMixin, View):
    """Open printable version of the discharge summary in a new tab."""

    def get(self, request, summary_id):
        summary = get_object_or_404(
            DischargeSummary.objects.select_related(
                "admission",
                "admission__patient",
                "admission__ward",
                "admission__room",
                "admission__bed",
                "admission__visit",
                "created_by",
                "finalized_by",
            ),
            pk=summary_id,
        )

        admission = summary.admission
        labs, rads = services.get_investigations_for_visit(admission.visit)
        treatments = services.get_treatments_for_admission(admission)
        billing = get_admission_billing_summary(admission)

        from core.models import HospitalSetting
        hospital = HospitalSetting.load()

        return render(request, "discharge/print.html", {
            "summary": summary,
            "admission": admission,
            "hospital": hospital,
            "labs": labs,
            "rads": rads,
            "treatments": treatments,
            "billing": billing,
        })


class AdmissionForDischargeListView(LoginRequiredMixin, View):
    """Show admitted patients eligible for discharge summary creation."""

    def get(self, request):
        from admission.models import Admission
        admitted = (
            Admission.objects
            .filter(status=Admission.Status.ADMITTED)
            .select_related("patient", "ward", "room", "bed", "visit")
            .order_by("-admission_date")
        )
        summaries = DischargeSummary.objects.select_related(
            "admission",
        ).in_bulk(field_name="admission_id")

        patient_data = []
        for adm in admitted:
            ds = summaries.get(adm.pk)
            patient_data.append({
                "admission": adm,
                "discharge_summary": ds,
                "has_summary": ds is not None,
            })

        return render(request, "discharge/admission_list.html", {
            "patient_data": patient_data,
        })


class DiagnosisSuggestionsAPIView(LoginRequiredMixin, View):
    """Return diagnosis suggestions from consultation history and common diagnoses."""

    COMMON_DIAGNOSES = [
        "Malaria", "Pneumonia", "Typhoid", "Diabetes Mellitus",
        "Hypertension", "Urinary Tract Infection", "Gastroenteritis",
        "Anemia", "HIV/AIDS", "Tuberculosis", "Asthma",
        "Chronic Obstructive Pulmonary Disease", "Heart Failure",
        "Cerebrovascular Accident", "Peptic Ulcer Disease",
        "Acute Appendicitis", "Acute Gastritis", "Pneumothorax",
        "Cellulitis", "Abscess", "Fracture", "Wound Infection",
        "Meningitis", "Hepatitis", "Renal Failure",
        "Sepsis", "Dehydration", "Malnutrition",
    ]

    def get(self, request):
        q = request.GET.get("q", "").strip()
        if len(q) < 2:
            return JsonResponse({"results": []})

        # Get diagnoses from past consultations
        from consultation.models import Consultation
        past_diagnoses = (
            Consultation.objects
            .filter(diagnosis__icontains=q)
            .values_list("diagnosis", flat=True)
            .distinct()[:10]
        )

        # Filter common diagnoses
        common = [d for d in self.COMMON_DIAGNOSES if q.lower() in d.lower()]

        # Merge and deduplicate
        seen = set()
        results = []
        for d in list(past_diagnoses) + common:
            d = d.strip()
            if d and d.lower() not in seen:
                seen.add(d.lower())
                results.append(d)

        return JsonResponse({"results": results[:15]})
