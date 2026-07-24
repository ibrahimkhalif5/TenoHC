"""
Service layer for billing app.
"""
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum

from .models import Invoice, InvoiceItem


def generate_invoice_number():
    """Generate unique invoice number: INV-YYYY-NNNNNN."""
    from datetime import date
    year = date.today().year
    prefix = f"INV-{year}-"

    with transaction.atomic():
        last = (
            Invoice.objects
            .select_for_update()
            .filter(invoice_number__startswith=prefix)
            .order_by("-invoice_number")
            .first()
        )
        if last:
            last_seq = int(last.invoice_number.split("-")[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1
        return f"{prefix}{next_seq:06d}"


def create_registration_invoice(patient, visit, amount, user=None):
    """Create an invoice for registration fee.
    Price is retrieved from Item Master if available."""
    from core.models import Item
    reg_item = Item.objects.filter(
        category=Item.Category.REGISTRATION, is_active=True,
    ).first()
    if reg_item:
        amount = reg_item.unit_price

    invoice_number = generate_invoice_number()
    invoice = Invoice.objects.create(
        patient=patient,
        visit=visit,
        invoice_number=invoice_number,
        total_amount=amount,
        amount_paid=0,
        status=Invoice.Status.PENDING,
        created_by=user,
    )
    InvoiceItem.objects.create(
        invoice=invoice,
        item=reg_item,
        description="Registration Fee",
        quantity=1,
        unit_price=amount,
    )
    return invoice


def get_invoice(invoice_id):
    """Get invoice with patient and items."""
    return (
        Invoice.objects
        .select_related("patient", "visit", "created_by")
        .prefetch_related("items")
        .get(pk=invoice_id)
    )


def get_or_create_visit_invoice(visit, user=None):
    """Get or create an invoice for a visit."""
    invoice, created = Invoice.objects.get_or_create(
        visit=visit,
        defaults={
            "patient": visit.patient,
            "invoice_number": generate_invoice_number(),
            "status": Invoice.Status.PENDING,
            "created_by": user,
        },
    )
    return invoice


def add_invoice_item(invoice, description, quantity=1, unit_price=0, item=None):
    """Add a line item to an invoice and update total.
    If item is provided, price is retrieved from Item Master."""
    if item and unit_price == 0:
        unit_price = item.unit_price
    item_obj = InvoiceItem.objects.create(
        invoice=invoice,
        item=item,
        description=description,
        quantity=quantity,
        unit_price=unit_price,
    )
    invoice.total_amount = sum(i.total_price for i in invoice.items.all())
    invoice.save(update_fields=["total_amount", "updated_at"])
    return item_obj


def get_visit_billing_summary(visit):
    """Get billing summary for a visit (all invoices combined).
    Returns dict with total_billed, nhif_rebate, total_paid, outstanding."""
    invoices = Invoice.objects.filter(visit=visit).exclude(
        status=Invoice.Status.CANCELLED,
    )
    agg = invoices.aggregate(
        total_billed=Sum("total_amount", default=Decimal("0")),
        total_rebate=Sum("nhif_rebate", default=Decimal("0")),
        total_paid=Sum("amount_paid", default=Decimal("0")),
    )
    total_billed = agg["total_billed"]
    total_rebate = agg["total_rebate"]
    total_paid = agg["total_paid"]
    outstanding = max(total_billed - total_rebate - total_paid, Decimal("0"))

    return {
        "total_billed": total_billed,
        "nhif_rebate": total_rebate,
        "total_paid": total_paid,
        "outstanding": outstanding,
        "invoice_count": invoices.count(),
    }


def get_admission_billing_summary(admission):
    """Get billing summary for an admission, including ward charges and NHIF/SHA rebate.

    NHIF/SHA Bed Rebate applies ONLY if:
      - Patient payment_type == INSURANCE
      - Patient is an inpatient (has an active/recent admission)

    Formula:
      Outstanding Before Rebate = Total Hospital Bill - Amount Paid
      NHIF/SHA Bed Rebate = Nights Stayed × Rebate Per Night  (from HospitalSetting)
      Final Balance = Outstanding Before Rebate - NHIF/SHA Bed Rebate
      Final Balance >= 0  (never negative)
    """
    from core.models import HospitalSetting
    from patients.models import Patient

    hospital = HospitalSetting.load()
    visit_billing = get_visit_billing_summary(admission.visit)

    ward_charge = admission.ward_charge or Decimal("0")
    total_billed = visit_billing["total_billed"] + ward_charge
    total_paid = visit_billing["total_paid"]

    # Determine if NHIF/SHA bed rebate applies
    is_insured = admission.patient.payment_type == Patient.PaymentType.INSURANCE
    is_inpatient = admission.status in ("ADMITTED", "DISCHARGED")
    rebate_per_night = hospital.nhif_sha_rebate_per_night or Decimal("0")
    nights = admission.nights_stayed or 0

    if is_insured and is_inpatient and rebate_per_night > 0:
        nhif_bed_rebate = Decimal(str(nights)) * rebate_per_night
    else:
        nhif_bed_rebate = Decimal("0")

    outstanding_before_rebate = max(total_billed - total_paid, Decimal("0"))
    final_balance = max(outstanding_before_rebate - nhif_bed_rebate, Decimal("0"))

    return {
        "total_billed": total_billed,
        "ward_charge": ward_charge,
        "other_charges": visit_billing["total_billed"],
        "nights_stayed": nights,
        "price_per_night": admission.ward.price_per_night,
        "invoice_count": visit_billing["invoice_count"],
        "nhif_bed_rebate": nhif_bed_rebate,
        "rebate_per_night": rebate_per_night,
        "total_paid": total_paid,
        "outstanding_before_rebate": outstanding_before_rebate,
        "final_balance": final_balance,
        "is_insured": is_insured,
        "is_inpatient": is_inpatient,
    }
