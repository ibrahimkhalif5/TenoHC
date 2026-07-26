from .constants import HOSPITAL_STAFF


def global_context(request):
    """Add global context variables to all templates."""
    return {
        "app_name": "THHIMS",
        "app_full_name": "TENOCARE HOSPITAL Information Management System",
        "staff": HOSPITAL_STAFF,
        "cashier_name": HOSPITAL_STAFF["CASHIER"],
        "doctor_name": HOSPITAL_STAFF["DOCTOR"],
        "lab_tech_name": HOSPITAL_STAFF["LAB_TECHNICIAN"],
        "radiologist_name": HOSPITAL_STAFF["RADIOLOGIST"],
    }
