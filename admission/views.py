from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.http import JsonResponse
from django.db.models import Count, Q

from .models import Ward, Room, Bed, Admission
from .forms import AdmissionForm, WardForm, RoomForm, BedForm
from . import services


class AdmissionQueueView(LoginRequiredMixin, View):
    """Display patients waiting for admission."""

    def get(self, request):
        from triage.models import Visit
        queue = (
            Visit.objects
            .filter(status=Visit.Status.ADMISSION_IN_PROGRESS)
            .select_related("patient", "patient__patient_category")
            .order_by("created_at")
        )
        admitted = (
            Admission.objects
            .filter(status=Admission.Status.ADMITTED)
            .select_related("patient", "ward", "room", "bed", "visit")
            .order_by("-admission_date")
        )
        return render(request, "admission/queue.html", {
            "visits": queue,
            "queue_count": queue.count(),
            "admitted_patients": admitted,
            "admitted_count": admitted.count(),
        })


class AdmissionCreateView(LoginRequiredMixin, View):
    """Admit a patient: select ward, room, bed."""

    def get(self, request, visit_id):
        from triage.models import Visit
        visit = get_object_or_404(Visit.objects.select_related("patient", "patient__patient_category"), pk=visit_id)
        wards = services.get_all_wards()
        form = AdmissionForm()
        return render(request, "admission/admit.html", {
            "visit": visit,
            "patient": visit.patient,
            "form": form,
            "wards": wards,
        })

    def post(self, request, visit_id):
        form = AdmissionForm(request.POST)
        if form.is_valid():
            try:
                admission = services.admit_patient(
                    visit_id=visit_id,
                    ward_id=form.cleaned_data["ward_id"].pk,
                    room_id=form.cleaned_data["room_id"].pk,
                    bed_id=form.cleaned_data["bed_id"].pk,
                    diagnosis=form.cleaned_data.get("diagnosis", ""),
                    notes=form.cleaned_data.get("notes", ""),
                    user=request.user,
                )
                messages.success(
                    request,
                    f"{admission.patient.full_name} admitted to {admission.ward.name} "
                    f"- Room {admission.room.room_number} Bed {admission.bed.bed_number}.",
                )
                return redirect("admission:admission-list")
            except Exception as e:
                messages.error(request, f"Admission failed: {e}")
        else:
            messages.error(request, "Please correct the errors below.")

        from triage.models import Visit
        visit = get_object_or_404(Visit.objects.select_related("patient"), pk=visit_id)
        return render(request, "admission/admit.html", {
            "visit": visit,
            "patient": visit.patient,
            "form": form,
            "wards": services.get_all_wards(),
        })


class AdmissionDischargeView(LoginRequiredMixin, View):
    """Discharge a patient."""

    def get(self, request, admission_id):
        admission = get_object_or_404(Admission.objects.select_related(
            "patient", "ward", "room", "bed", "visit",
        ), pk=admission_id)
        return render(request, "admission/discharge.html", {
            "admission": admission,
        })

    def post(self, request, admission_id):
        try:
            admission, nights, total_charge = services.discharge_patient(
                admission_id=admission_id, user=request.user,
            )
            messages.success(
                request,
                f"{admission.patient.full_name} discharged after {nights} night(s). "
                f"Total ward charge: KSh {total_charge:,.2f}",
            )
        except Exception as e:
            messages.error(request, f"Discharge failed: {e}")
        return redirect("admission:admission-list")


# ─── Ward Management Views ───────────────────────────────────────────

class WardManageView(LoginRequiredMixin, View):
    """Manage wards, rooms, beds."""

    def get(self, request):
        wards = (
            Ward.objects
            .filter(is_active=True)
            .prefetch_related("rooms__beds")
            .annotate(
                available_bed_count=Count(
                    "rooms__beds",
                    filter=Q(rooms__beds__is_occupied=False, rooms__beds__is_active=True),
                ),
                total_bed_count=Count(
                    "rooms__beds",
                    filter=Q(rooms__beds__is_active=True),
                ),
            )
        )
        ward_form = WardForm()
        room_form = RoomForm()
        bed_form = BedForm()
        return render(request, "admission/ward_manage.html", {
            "wards": wards,
            "ward_form": ward_form,
            "room_form": room_form,
            "bed_form": bed_form,
        })


class WardCreateView(LoginRequiredMixin, View):
    def post(self, request):
        form = WardForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ward created successfully.")
        else:
            messages.error(request, "Failed to create ward.")
        return redirect("admission:ward-manage")


class WardEditView(LoginRequiredMixin, View):
    def get(self, request, ward_id):
        ward = get_object_or_404(Ward, pk=ward_id)
        form = WardForm(instance=ward)
        return render(request, "admission/ward_edit.html", {"ward": ward, "form": form})

    def post(self, request, ward_id):
        ward = get_object_or_404(Ward, pk=ward_id)
        form = WardForm(request.POST, instance=ward)
        if form.is_valid():
            form.save()
            messages.success(request, "Ward updated successfully.")
        return redirect("admission:ward-manage")


class RoomCreateView(LoginRequiredMixin, View):
    def post(self, request):
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Room created successfully.")
        else:
            messages.error(request, "Failed to create room.")
        return redirect("admission:ward-manage")


class BedCreateView(LoginRequiredMixin, View):
    def post(self, request):
        form = BedForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Bed created successfully.")
        else:
            messages.error(request, "Failed to create bed.")
        return redirect("admission:ward-manage")


# ─── API ──────────────────────────────────────────────────────────────

class RoomListAPIView(LoginRequiredMixin, View):
    """JSON endpoint: available rooms for a ward."""

    def get(self, request):
        ward_id = request.GET.get("ward_id")
        if not ward_id:
            return JsonResponse([], safe=False)
        rooms = (
            Room.objects
            .filter(ward_id=ward_id, is_active=True)
            .annotate(
                available_bed_count=Count(
                    "beds", filter=Q(beds__is_occupied=False, beds__is_active=True),
                ),
            )
        )
        data = [
            {"id": r.id, "room_number": r.room_number, "room_type": r.get_room_type_display(),
             "available_beds": r.available_bed_count}
            for r in rooms
        ]
        return JsonResponse(data, safe=False)


class BedListAPIView(LoginRequiredMixin, View):
    """JSON endpoint: available beds for a room."""

    def get(self, request):
        room_id = request.GET.get("room_id")
        if not room_id:
            return JsonResponse([], safe=False)
        beds = services.get_available_beds(room_id)
        data = [
            {"id": b.id, "bed_number": b.bed_number}
            for b in beds
        ]
        return JsonResponse(data, safe=False)
