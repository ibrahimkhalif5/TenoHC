from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from consultation.models import Prescription
from .models import PharmacyDispense
from .forms import DispenseConfirmForm
from . import services


class PharmacyQueueView(LoginRequiredMixin, View):
    """Display patients waiting for pharmacy."""

    def get(self, request):
        queue = services.get_pharmacy_queue()
        return render(request, "pharmacy/queue.html", {
            "visits": queue,
            "queue_count": queue.count(),
        })


class PharmacyDispenseView(LoginRequiredMixin, View):
    """Display a patient's prescriptions for dispensing."""

    def get(self, request, visit_id):
        visit = services.get_visit_for_dispensing(visit_id)
        pending_prescriptions = services.get_undispensed_prescriptions(visit_id)
        dispense_history = services.get_dispense_history(visit_id)

        return render(request, "pharmacy/dispense.html", {
            "visit": visit,
            "patient": visit.patient,
            "pending_prescriptions": pending_prescriptions,
            "dispense_history": dispense_history,
            "form": DispenseConfirmForm(),
        })


class DispenseSingleView(LoginRequiredMixin, View):
    """Dispense a single prescription."""

    def post(self, request, prescription_id):
        prescription = get_object_or_404(
            Prescription.objects.select_related(
                "consultation__visit__patient",
                "medicine",
            ),
            pk=prescription_id,
        )

        if prescription.is_dispensed:
            messages.error(request, f"{prescription.medicine.name} has already been dispensed.")
            return redirect("pharmacy:pharmacy-dispense", visit_id=prescription.consultation.visit.pk)

        visit_id = prescription.consultation.visit.pk

        try:
            dispense = services.dispense_prescription(
                prescription_id=prescription.pk,
                user=request.user,
            )
            messages.success(
                request,
                f"{prescription.medicine.name} x{prescription.quantity} dispensed successfully.",
            )
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Dispensing failed: {e}")

        from triage.models import Visit
        visit = Visit.objects.filter(pk=visit_id).first()
        if visit and visit.status == Visit.Status.COMPLETED:
            messages.success(request, "All prescriptions dispensed. Visit completed!")
            return redirect("pharmacy:pharmacy-list")

        return redirect("pharmacy:pharmacy-dispense", visit_id=visit_id)


class DispenseAllView(LoginRequiredMixin, View):
    """Dispense all pending prescriptions for a visit."""

    def post(self, request, visit_id):
        try:
            results = services.dispense_all_pending(visit_id, user=request.user)
            messages.success(
                request,
                f"All {len(results)} prescription(s) dispensed successfully.",
            )
        except ValueError as e:
            messages.error(request, str(e))

        from triage.models import Visit
        visit = Visit.objects.filter(pk=visit_id).first()
        if visit and visit.status == Visit.Status.COMPLETED:
            messages.success(request, "All prescriptions dispensed. Visit completed!")
            return redirect("pharmacy:pharmacy-list")

        return redirect("pharmacy:pharmacy-dispense", visit_id=visit_id)


class DispenseHistoryView(LoginRequiredMixin, View):
    """View dispensing history for a visit."""

    def get(self, request, visit_id):
        from triage.models import Visit
        visit = get_object_or_404(
            Visit.objects.select_related("patient"), pk=visit_id,
        )
        dispenses = services.get_dispense_history(visit_id)
        return render(request, "pharmacy/history.html", {
            "visit": visit,
            "patient": visit.patient,
            "dispenses": dispenses,
        })


class FinishVisitView(LoginRequiredMixin, View):
    """Explicitly finish a visit after all prescriptions are dispensed."""

    def post(self, request, visit_id):
        try:
            services.finish_visit(visit_id, user=request.user)
            messages.success(request, "Visit completed successfully.")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("pharmacy:pharmacy-list")
