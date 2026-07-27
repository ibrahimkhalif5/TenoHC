from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View

from .models import Consultation
from .forms import ConsultationForm, PrescriptionFormSet
from . import services


class DoctorQueueView(LoginRequiredMixin, View):
    """Display patients waiting for doctor (initial or review)."""

    def get(self, request):
        queue = services.get_doctor_queue()
        return render(request, "consultation/queue.html", {
            "visits": queue,
            "queue_count": queue.count(),
        })


class StartConsultationView(LoginRequiredMixin, View):
    """Start a consultation for a patient."""

    def post(self, request, visit_id):
        try:
            consultation = services.start_consultation(
                visit_id=visit_id, user=request.user,
            )
            return redirect(
                "consultation:conduct-consultation",
                consultation_id=consultation.pk,
            )
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("consultation:consultation-list")


class ConductConsultationView(LoginRequiredMixin, View):
    """Conduct a consultation: diagnosis, tests, prescriptions."""

    def get(self, request, consultation_id):
        consultation = get_object_or_404(
            Consultation.objects.select_related(
                "visit", "visit__patient", "doctor",
            ).prefetch_related(
                "prescriptions", "prescriptions__medicine",
            ),
            pk=consultation_id,
        )

        visit = consultation.visit
        from triage.models import TriageAssessment
        triage = (
            TriageAssessment.objects
            .filter(visit=visit)
            .order_by("-assessed_at")
            .first()
        )

        form = ConsultationForm(instance=consultation)
        prescription_formset = PrescriptionFormSet(
            prefix="prescriptions",
        )

        from laboratory.models import LabRequest
        from radiology.models import RadiologyRequest

        is_review = visit.status == "WAITING_DOCTOR_REVIEW"

        previous_lab_requests = LabRequest.objects.filter(
            visit=visit,
        ).select_related("lab_test", "completed_by").prefetch_related(
            "result_values__parameter"
        ).order_by("-created_at")
        previous_rad_requests = RadiologyRequest.objects.filter(
            visit=visit,
        ).select_related("radiology_service", "completed_by").order_by("-created_at")

        previous_consultations = Consultation.objects.filter(
            visit=visit,
        ).exclude(pk=consultation.pk).select_related("doctor").order_by("-started_at")

        from triage.services import get_visit_timeline
        timeline = get_visit_timeline(visit)

        return render(request, "consultation/conduct.html", {
            "consultation": consultation,
            "visit": visit,
            "patient": visit.patient,
            "triage": triage,
            "form": form,
            "prescription_formset": prescription_formset,
            "is_review": is_review,
            "previous_lab_requests": previous_lab_requests,
            "previous_rad_requests": previous_rad_requests,
            "previous_consultations": previous_consultations,
            "timeline": timeline,
        })

    def post(self, request, consultation_id):
        consultation = get_object_or_404(Consultation, pk=consultation_id)
        action = request.POST.get("action", "complete")

        form = ConsultationForm(request.POST, instance=consultation)

        if action == "order_tests":
            if form.is_valid():
                form.save()
                item_ids = request.POST.getlist("lab_tests")
                rad_item_ids = request.POST.getlist("radiology_services")
                diagnosis = form.cleaned_data.get("diagnosis", "")
                notes = form.cleaned_data.get("notes", "")

                if not item_ids and not rad_item_ids:
                    messages.warning(request, "Please select at least one test to order.")
                    return redirect(
                        "consultation:conduct-consultation",
                        consultation_id=consultation.pk,
                    )

                from core.models import Item
                from laboratory.models import LabTest
                from radiology.models import RadiologyService

                lab_test_ids = []
                for iid in item_ids:
                    try:
                        item = Item.objects.get(pk=iid, is_active=True)
                    except (Item.DoesNotExist, ValueError):
                        continue
                    lt = LabTest.objects.filter(item=item).first()
                    if not lt:
                        lt = LabTest.objects.create(
                            item=item,
                            name=item.name,
                            category="OTHER",
                            price=item.unit_price,
                            description=item.description,
                            normal_range=item.normal_range,
                            unit=item.unit,
                        )
                    lab_test_ids.append(str(lt.pk))

                rad_svc_ids = []
                for rid in rad_item_ids:
                    try:
                        item = Item.objects.get(pk=rid, is_active=True)
                    except (Item.DoesNotExist, ValueError):
                        continue
                    svc = RadiologyService.objects.filter(item=item).first()
                    if not svc:
                        svc_type = "OTHER"
                        if item.category == Item.Category.ULTRASOUND:
                            svc_type = "ULTRASOUND"
                        elif item.category == Item.Category.RADIOLOGY:
                            svc_type = "XRAY"
                        svc = RadiologyService.objects.create(
                            item=item,
                            name=item.name,
                            service_type=svc_type,
                            price=item.unit_price,
                            description=item.description,
                        )
                    rad_svc_ids.append(str(svc.pk))

                consultation, lab_count, rad_count = services.order_tests(
                    consultation_id=consultation.pk,
                    lab_test_ids=lab_test_ids,
                    radiology_service_ids=rad_svc_ids,
                    diagnosis=diagnosis,
                    notes=notes,
                    user=request.user,
                )

                parts = []
                if lab_count:
                    parts.append(f"{lab_count} lab test(s)")
                if rad_count:
                    parts.append(f"{rad_count} radiology order(s)")

                messages.success(
                    request,
                    f"Tests ordered: {', '.join(parts)}. Patient sent for testing.",
                )
                return redirect("consultation:consultation-list")
            else:
                messages.error(request, "Please correct the errors below.")

        elif action == "admit":
            if form.is_valid():
                form.save()
                prescription_formset = PrescriptionFormSet(
                    request.POST, prefix="prescriptions",
                )
                prescriptions_data = _extract_prescriptions(prescription_formset)

                services.complete_consultation(
                    consultation_id=consultation.pk,
                    prescriptions_data=prescriptions_data,
                    request_admission=True,
                    diagnosis=form.cleaned_data.get("diagnosis", ""),
                    notes=form.cleaned_data.get("notes", ""),
                    treatment_plan=form.cleaned_data.get("treatment_plan", ""),
                    user=request.user,
                )
                messages.success(request, "Patient referred for admission.")
                return redirect("consultation:consultation-list")
            else:
                messages.error(request, "Please correct the errors below.")

        else:
            if form.is_valid():
                prescription_formset = PrescriptionFormSet(
                    request.POST, prefix="prescriptions",
                )
                prescriptions_data = _extract_prescriptions(prescription_formset)

                services.complete_consultation(
                    consultation_id=consultation.pk,
                    prescriptions_data=prescriptions_data,
                    diagnosis=form.cleaned_data.get("diagnosis", ""),
                    notes=form.cleaned_data.get("notes", ""),
                    treatment_plan=form.cleaned_data.get("treatment_plan", ""),
                    user=request.user,
                )
                messages.success(request, "Consultation completed successfully.")
                return redirect("consultation:consultation-list")
            else:
                messages.error(request, "Please correct the errors below.")

        return redirect(
            "consultation:conduct-consultation",
            consultation_id=consultation.pk,
        )


def _extract_prescriptions(formset):
    """Extract prescription data from simplified formset."""
    from core.models import Item
    from inventory.models import Medicine

    data = []
    for form in formset:
        if not form.is_valid():
            continue
        item_id = form.cleaned_data.get("medicine")
        if not item_id:
            continue

        try:
            item = Item.objects.get(pk=item_id, category=Item.Category.MEDICINE, is_active=True)
        except (Item.DoesNotExist, ValueError, TypeError):
            continue

        medicine, _ = Medicine.objects.get_or_create(
            item=item,
            defaults={"name": item.name, "selling_price": item.unit_price, "is_active": True},
        )

        dosage = form.cleaned_data.get("dosage", "")
        frequency = form.cleaned_data.get("frequency", "")
        duration = form.cleaned_data.get("duration_days", 1)

        qty = 1
        freq_lower = frequency.lower().strip()
        if "qds" in freq_lower or "4 times" in freq_lower:
            qty = 4
        elif "tds" in freq_lower or "tid" in freq_lower or "3 times" in freq_lower:
            qty = 3
        elif "bd" in freq_lower or "bid" in freq_lower or "2 times" in freq_lower:
            qty = 2
        else:
            qty = 1
        qty = qty * duration

        dosage_unit = "TABLET"
        dl = dosage.lower()
        if "mg" in dl:
            dosage_unit = "MG"
        elif "ml" in dl:
            dosage_unit = "ML"
        elif "drop" in dl:
            dosage_unit = "DROP"
        elif "puff" in dl:
            dosage_unit = "PUFF"
        elif "unit" in dl:
            dosage_unit = "UNIT"
        elif "capsule" in dl:
            dosage_unit = "CAPSULE"

        data.append({
            "medicine_id": medicine.pk,
            "dosage": dosage,
            "dosage_unit": dosage_unit,
            "frequency": frequency,
            "duration_days": duration,
            "quantity": qty,
            "route": "Oral",
            "instructions": "",
        })
    return data


class ConsultationDetailView(LoginRequiredMixin, View):
    """View completed consultation details."""

    def get(self, request, consultation_id):
        consultation = get_object_or_404(
            Consultation.objects.select_related(
                "visit", "visit__patient", "doctor",
            ).prefetch_related(
                "prescriptions", "prescriptions__medicine",
            ),
            pk=consultation_id,
        )
        visit = consultation.visit
        from triage.services import get_visit_timeline
        timeline = get_visit_timeline(visit)

        return render(request, "consultation/detail.html", {
            "consultation": consultation,
            "patient": visit.patient,
            "timeline": timeline,
        })


class ConsultationHistoryView(LoginRequiredMixin, View):
    """View all consultations for a visit."""

    def get(self, request, visit_id):
        from triage.models import Visit
        visit = get_object_or_404(
            Visit.objects.select_related("patient"),
            pk=visit_id,
        )
        consultations = services.get_visit_consultations(visit)
        from triage.services import get_visit_timeline
        timeline = get_visit_timeline(visit)

        return render(request, "consultation/history.html", {
            "visit": visit,
            "consultations": consultations,
            "timeline": timeline,
        })


class ConsultationPrintView(LoginRequiredMixin, View):
    """Print-friendly view of patient details + lab/radiology reports."""

    def get(self, request, consultation_id):
        consultation = get_object_or_404(
            Consultation.objects.select_related(
                "visit", "visit__patient", "doctor",
            ).prefetch_related(
                "prescriptions", "prescriptions__medicine",
            ),
            pk=consultation_id,
        )
        visit = consultation.visit
        patient = visit.patient

        previous_lab_requests = visit.lab_requests.select_related(
            "lab_test", "completed_by",
        ).prefetch_related("result_values__parameter").order_by("-created_at")

        previous_rad_requests = visit.radiology_requests.select_related(
            "radiology_service", "completed_by",
        ).order_by("-created_at")

        previous_consultations = Consultation.objects.filter(
            visit=visit,
        ).exclude(pk=consultation.pk).select_related("doctor").order_by("-started_at")

        from triage.services import get_visit_timeline
        timeline = get_visit_timeline(visit)

        return render(request, "consultation/print.html", {
            "consultation": consultation,
            "visit": visit,
            "patient": patient,
            "previous_lab_requests": previous_lab_requests,
            "previous_rad_requests": previous_rad_requests,
            "previous_consultations": previous_consultations,
            "timeline": timeline,
        })


class GeneralReportView(LoginRequiredMixin, View):
    """General printable report: lab tests, radiology, prescriptions, pharmacy dispenses."""

    def get(self, request, consultation_id):
        consultation = get_object_or_404(
            Consultation.objects.select_related(
                "visit", "visit__patient", "doctor",
            ).prefetch_related(
                "prescriptions", "prescriptions__medicine",
            ),
            pk=consultation_id,
        )
        visit = consultation.visit
        patient = visit.patient

        from laboratory.models import LabRequest
        from radiology.models import RadiologyRequest
        from pharmacy.models import PharmacyDispense

        lab_requests = LabRequest.objects.filter(
            visit=visit,
        ).select_related("lab_test", "completed_by").prefetch_related(
            "result_values__parameter"
        ).order_by("-created_at")

        rad_requests = RadiologyRequest.objects.filter(
            visit=visit,
        ).select_related("radiology_service", "completed_by").order_by("-created_at")

        prescriptions = consultation.prescriptions.select_related("medicine").order_by("created_at")

        dispenses = PharmacyDispense.objects.filter(
            visit=visit,
        ).select_related("medicine", "prescription", "dispensed_by").order_by("-dispensed_at")

        return render(request, "consultation/general_report.html", {
            "consultation": consultation,
            "visit": visit,
            "patient": patient,
            "lab_requests": lab_requests,
            "rad_requests": rad_requests,
            "prescriptions": prescriptions,
            "dispenses": dispenses,
        })
