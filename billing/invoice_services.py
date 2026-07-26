"""
Invoice services: aggregates all billable items from every department
for a given visit, and provides PDF/DOCX generation.
"""
from decimal import Decimal
from collections import OrderedDict
from core.constants import CASHIER_NAME, DOCTOR_NAME


def get_invoice_data(invoice):
    """
    Build a complete invoice data dictionary by pulling all billable
    items from the database for the invoice's visit.

    Returns a dict with all sections needed for rendering.
    """
    from core.models import HospitalSetting
    from billing.models import Invoice, InvoiceItem
    from cashier.models import Payment
    from consultation.models import Consultation, Prescription
    from laboratory.models import LabRequest
    from radiology.models import RadiologyRequest
    from pharmacy.models import PharmacyDispense
    from admission.models import Admission
    from nursing.models import Treatment
    from triage.models import Visit

    patient = invoice.patient
    visit = invoice.visit
    hospital = HospitalSetting.load()

    # ── Is this an inpatient visit? ──
    admission = Admission.objects.filter(visit=visit).select_related(
        "ward", "room", "bed", "admitted_by", "discharged_by",
    ).first()
    is_inpatient = admission is not None

    # ── Consultation info ──
    consultation = Consultation.objects.filter(visit=visit).select_related(
        "doctor",
    ).order_by("created_at").first()

    # ── Diagnosis from consultation ──
    primary_diagnosis = ""
    secondary_diagnosis = ""
    if consultation:
        diag_text = consultation.diagnosis or ""
        lines = [l.strip() for l in diag_text.split("\n") if l.strip()]
        if lines:
            primary_diagnosis = lines[0]
        if len(lines) > 1:
            secondary_diagnosis = "\n".join(lines[1:])

    # ── Discharge summary (for diagnosis if no consultation) ──
    if not primary_diagnosis and admission:
        from discharge.models import DischargeSummary
        ds = DischargeSummary.objects.filter(admission=admission).first()
        if ds:
            primary_diagnosis = ds.primary_diagnosis
            secondary_diagnosis = ds.secondary_diagnosis

    # ── Build service items from invoice items (already stored) ──
    invoice_items = list(
        InvoiceItem.objects.filter(invoice=invoice).order_by("created_at")
    )

    services_section = []
    lab_section = []
    radiology_section = []
    medication_section = []
    ward_section = None
    nursing_section = []
    other_section = []

    # Categorize existing invoice items
    for item in invoice_items:
        desc_lower = item.description.lower()
        if "registration" in desc_lower:
            services_section.append({
                "date": invoice.created_at.strftime("%d %b %Y") if invoice.created_at else "",
                "department": "Registration",
                "service": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.total_price,
            })
        elif "consultation" in desc_lower:
            services_section.append({
                "date": invoice.created_at.strftime("%d %b %Y") if invoice.created_at else "",
                "department": "Consultation",
                "service": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.total_price,
            })
        elif "lab" in desc_lower or "test" in desc_lower:
            lab_section.append({
                "test_name": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.total_price,
                "status": "Completed",
            })
        elif "x-ray" in desc_lower or "xray" in desc_lower or "ultrasound" in desc_lower or "radiology" in desc_lower or "mri" in desc_lower or "ct scan" in desc_lower:
            radiology_section.append({
                "service": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.total_price,
            })
        elif "medicine" in desc_lower or "drug" in desc_lower or "pharmacy" in desc_lower or "dispense" in desc_lower:
            medication_section.append({
                "medicine_name": item.description,
                "dosage": "",
                "frequency": "",
                "duration": "",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.total_price,
            })
        elif "ward" in desc_lower or "room" in desc_lower or "bed" in desc_lower:
            ward_section = {
                "ward_type": item.description,
                "room_number": admission.room.room_number if admission else "",
                "bed_number": admission.bed.bed_number if admission else "",
                "admission_date": admission.admission_date.strftime("%d %b %Y") if admission and admission.admission_date else "",
                "discharge_date": admission.discharge_date.strftime("%d %b %Y") if admission and admission.discharge_date else "",
                "length_of_stay": admission.nights_stayed if admission else 0,
                "ward_rate": admission.ward.price_per_night if admission else Decimal("0"),
                "total_charges": item.total_price,
            }
        elif "nursing" in desc_lower or "care" in desc_lower:
            nursing_section.append({
                "service": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.total_price,
            })
        else:
            other_section.append({
                "service": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.total_price,
            })

    # ── Enrich with pharmacy dispense data if available ──
    if not medication_section:
        dispenses = PharmacyDispense.objects.filter(
            visit=visit,
        ).select_related("medicine", "prescription").order_by("dispensed_at")

        for d in dispenses:
            medication_section.append({
                "medicine_name": d.medicine.name,
                "dosage": d.medicine.strength or "",
                "frequency": d.prescription.frequency if d.prescription else "",
                "duration": f"{d.prescription.duration_days} days" if d.prescription and d.prescription.duration_days else "",
                "quantity": int(d.quantity_dispensed),
                "unit_price": d.charge / d.quantity_dispensed if d.quantity_dispensed else d.medicine.selling_price,
                "amount": d.charge,
            })

    # ── Enrich lab data from LabRequest if not already in invoice items ──
    if not lab_section:
        lab_requests = LabRequest.objects.filter(
            visit=visit, is_completed=True,
        ).select_related("lab_test").order_by("created_at")

        for lr in lab_requests:
            lab_section.append({
                "test_name": lr.lab_test.name,
                "quantity": 1,
                "unit_price": lr.lab_test.price,
                "amount": lr.lab_test.price,
                "status": "Completed",
            })

    # ── Enrich radiology data ──
    if not radiology_section:
        rad_requests = RadiologyRequest.objects.filter(
            visit=visit, is_completed=True,
        ).select_related("radiology_service").order_by("created_at")

        for rr in rad_requests:
            radiology_section.append({
                "service": rr.radiology_service.name,
                "quantity": 1,
                "unit_price": rr.radiology_service.price,
                "amount": rr.radiology_service.price,
            })

    # ── Enrich nursing data ──
    if not nursing_section and admission:
        treatments = Treatment.objects.filter(
            admission=admission,
        ).order_by("created_at")

        for t in treatments:
            nursing_section.append({
                "service": t.treatment,
                "quantity": 1,
                "unit_price": Decimal("0"),
                "amount": Decimal("0"),
            })

    # ── Calculate ward section if inpatient and not already set ──
    if is_inpatient and not ward_section and admission:
        nights = admission.nights_stayed
        rate = admission.ward.price_per_night
        total = nights * rate
        ward_section = {
            "ward_type": f"{admission.ward.name} ({admission.ward.get_ward_type_display()})",
            "room_number": admission.room.room_number,
            "bed_number": admission.bed.bed_number,
            "admission_date": admission.admission_date.strftime("%d %b %Y") if admission.admission_date else "",
            "discharge_date": admission.discharge_date.strftime("%d %b %Y") if admission.discharge_date else "Currently Admitted",
            "length_of_stay": nights,
            "ward_rate": rate,
            "total_charges": total,
        }

    # ── Payment history ──
    payments = list(
        Payment.objects.filter(invoice=invoice)
        .select_related("received_by")
        .order_by("created_at")
    )

    payment_history = []
    for p in payments:
        payment_history.append({
            "date": p.created_at.strftime("%d %b %Y %H:%M") if p.created_at else "",
            "receipt_number": p.receipt_number,
            "payment_method": p.get_payment_method_display(),
            "amount": p.amount,
            "cashier": CASHIER_NAME,
        })

    # ── Bill summary ──
    from patients.models import Patient

    reg_fee = sum(i.unit_price for i in invoice_items if "registration" in i.description.lower())
    consult_fee = sum(i.unit_price for i in invoice_items if "consultation" in i.description.lower())
    lab_charges = sum(i["amount"] for i in lab_section) if lab_section else sum(
        i.total_price for i in invoice_items if "lab" in i.description.lower() or "test" in i.description.lower()
    )
    rad_charges = sum(i["amount"] for i in radiology_section) if radiology_section else sum(
        i.total_price for i in invoice_items if any(k in i.description.lower() for k in ["x-ray", "xray", "ultrasound", "radiology", "mri", "ct scan"])
    )
    med_charges = sum(i["amount"] for i in medication_section) if medication_section else sum(
        i.total_price for i in invoice_items if any(k in i.description.lower() for k in ["medicine", "drug", "pharmacy", "dispense"])
    )
    ward_charges = sum(i.total_price for i in invoice_items if any(k in i.description.lower() for k in ["ward", "room", "bed"]))
    nursing_charges = sum(i["amount"] for i in nursing_section) if nursing_section else Decimal("0")
    procedure_charges = Decimal("0")
    other_charges = sum(i["amount"] for i in other_section) if other_section else Decimal("0")

    subtotal = invoice.total_amount
    amount_paid = invoice.amount_paid

    # ── NHIF/SHA Bed Rebate ──
    is_insured = patient.payment_type == Patient.PaymentType.INSURANCE
    is_inpatient_admission = is_inpatient and admission is not None
    rebate_per_night = hospital.nhif_sha_rebate_per_night or Decimal("0")
    nights = admission.nights_stayed if admission else 0

    if is_insured and is_inpatient_admission and rebate_per_night > 0:
        nhif_bed_rebate = Decimal(str(nights)) * rebate_per_night
    else:
        nhif_bed_rebate = Decimal("0")

    outstanding_before_rebate = max(subtotal - amount_paid, Decimal("0"))
    final_balance = max(outstanding_before_rebate - nhif_bed_rebate, Decimal("0"))

    # ── Visit type ──
    visit_type = "Inpatient" if is_inpatient else "Outpatient"

    # ── Attending doctor ──
    doctor_name = DOCTOR_NAME

    return {
        "hospital": hospital,
        "invoice": invoice,
        "patient": patient,
        "visit": visit,
        "admission": admission,
        "is_inpatient": is_inpatient,
        "visit_type": visit_type,
        "consultation": consultation,
        "doctor_name": doctor_name,
        "primary_diagnosis": primary_diagnosis,
        "secondary_diagnosis": secondary_diagnosis,
        "services": services_section,
        "lab_tests": lab_section,
        "radiology": radiology_section,
        "medications": medication_section,
        "ward": ward_section,
        "nursing": nursing_section,
        "other_charges": other_section,
        "payments": payment_history,
        "summary": {
            "registration_fee": reg_fee,
            "consultation_fee": consult_fee,
            "lab_charges": lab_charges,
            "radiology_charges": rad_charges,
            "medication_charges": med_charges,
            "ward_charges": ward_charges,
            "nursing_charges": nursing_charges,
            "procedure_charges": procedure_charges,
            "other_charges": other_charges,
            "subtotal": subtotal,
            "discount": Decimal("0"),
            "tax": Decimal("0"),
            "grand_total": subtotal,
            "amount_paid": amount_paid,
            "nhif_bed_rebate": nhif_bed_rebate,
            "rebate_per_night": rebate_per_night,
            "nights_stayed": nights,
            "outstanding_before_rebate": outstanding_before_rebate,
            "balance": final_balance,
            "is_insured": is_insured,
        },
    }
