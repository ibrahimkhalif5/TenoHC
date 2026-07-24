"""
Service layer for patients app.
"""
from django.db import transaction
from django.db.models import Q

from .models import Patient


def generate_patient_number():
    """Generate unique patient number: THH-YYYY-NNNNNN."""
    from datetime import date
    year = date.today().year
    prefix = f"THH-{year}-"

    with transaction.atomic():
        last = (
            Patient.objects
            .select_for_update()
            .filter(patient_number__startswith=prefix)
            .order_by("-patient_number")
            .first()
        )
        if last:
            last_seq = int(last.patient_number.split("-")[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1
        return f"{prefix}{next_seq:06d}"


def search_patients(query):
    """Search patients by name, phone, national_id, or patient_number."""
    if not query or not query.strip():
        return Patient.objects.filter(is_active=True)[:20]

    q = query.strip()
    return Patient.objects.filter(
        Q(first_name__icontains=q)
        | Q(last_name__icontains=q)
        | Q(middle_name__icontains=q)
        | Q(phone__icontains=q)
        | Q(national_id__icontains=q)
        | Q(patient_number__icontains=q)
    ).filter(is_active=True).select_related("patient_category")[:20]


def get_patient(patient_id):
    """Get patient by ID."""
    return Patient.objects.get(pk=patient_id)


def register_patient(form_data, user=None):
    """
    Register a new patient.
    Creates Patient + Visit (WAITING_TRIAGE) + Invoice (registration fee)
    all in a single atomic transaction.
    """
    from triage.models import Visit
    from billing.services import create_registration_invoice

    with transaction.atomic():
        patient_number = generate_patient_number()
        patient = Patient.objects.create(
            patient_number=patient_number,
            first_name=form_data["first_name"],
            last_name=form_data["last_name"],
            middle_name=form_data.get("middle_name", ""),
            gender=form_data["gender"],
            date_of_birth=form_data["date_of_birth"],
            phone=form_data["phone"],
            address=form_data["address"],
            national_id=form_data.get("national_id") or None,
            next_of_kin_name=form_data.get("next_of_kin_name", ""),
            next_of_kin_phone=form_data.get("next_of_kin_phone", ""),
            next_of_kin_relationship=form_data.get("next_of_kin_relationship", ""),
            patient_category=form_data.get("patient_category"),
            patient_type=form_data.get("patient_type", Patient.PatientType.NEW),
            payment_type=form_data.get("payment_type", "CASH"),
            registration_fee=form_data.get("registration_fee", 0),
            photo=form_data.get("photo"),
        )

        # Create first visit in triage queue
        from triage.services import generate_visit_number
        visit = Visit.objects.create(
            patient=patient,
            visit_number=generate_visit_number(),
            status=Visit.Status.WAITING_TRIAGE,
            created_by=user,
        )

        # Create registration fee invoice
        reg_fee = patient.registration_fee
        if reg_fee > 0:
            create_registration_invoice(patient, visit, reg_fee, user)

        return patient


def create_returning_visit(patient, user=None):
    """Create a new visit for an existing patient (WAITING_TRIAGE)."""
    from triage.models import Visit

    from triage.services import generate_visit_number
    visit = Visit.objects.create(
        patient=patient,
        visit_number=generate_visit_number(),
        status=Visit.Status.WAITING_TRIAGE,
        created_by=user,
    )
    return visit
