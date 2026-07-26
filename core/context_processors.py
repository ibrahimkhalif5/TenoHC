from .constants import HOSPITAL_STAFF


def global_context(request):
    """Add global context variables to all templates."""
    return {
        "app_name": "TCHIMS",
        "app_full_name": "TENOCARE HOSPITAL Information Management System",
        "staff": HOSPITAL_STAFF,
        "cashier_name": HOSPITAL_STAFF["CASHIER"],
        "doctor_name": HOSPITAL_STAFF["DOCTOR"],
        "lab_tech_name": HOSPITAL_STAFF["LAB_TECHNICIAN"],
        "radiologist_name": HOSPITAL_STAFF["RADIOLOGIST"],
    }


def sidebar_counts(request):
    """Provide live patient counts for sidebar badges."""
    if not request.user.is_authenticated:
        return {}

    from triage.models import Visit
    from laboratory.models import LabRequest
    from radiology.models import RadiologyRequest

    statuses = Visit.objects.values_list("status", flat=True)
    status_list = list(statuses)

    counts = {
        "count_triage": status_list.count(Visit.Status.WAITING_TRIAGE),
        "count_doctor": (
            status_list.count(Visit.Status.WAITING_DOCTOR)
            + status_list.count(Visit.Status.WAITING_DOCTOR_REVIEW)
            + status_list.count(Visit.Status.IN_CONSULTATION)
        ),
        "count_lab": LabRequest.objects.filter(is_completed=False).count(),
        "count_radiology": RadiologyRequest.objects.filter(is_completed=False).count(),
        "count_pharmacy": status_list.count(Visit.Status.WAITING_PHARMACY),
    }
    return counts
