from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Q


def _daterange(start_date, end_date):
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
    return start_date, end_date


def get_report(report_type, start_date=None, end_date=None):
    start_date, end_date = _daterange(start_date, end_date)
    fn = {
        "financial": _financial,
        "clinical": _clinical,
        "patients": _patients,
        "inventory": _inventory,
    }.get(report_type, _financial)
    return fn(start_date, end_date)


def _financial(start_date, end_date):
    from cashier.models import Payment
    from billing.models import Invoice

    payments = Payment.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    invoices = Invoice.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

    payment_total = payments.aggregate(t=Sum("amount"))["t"] or 0
    invoice_total = invoices.aggregate(t=Sum("total_amount"))["t"] or 0

    by_method = list(
        payments.values("payment_method")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    invoice_status = list(
        invoices.values("status")
        .annotate(count=Count("id"), total=Sum("total_amount"))
        .order_by("status")
    )

    return {
        "title": "Financial Report",
        "cards": [
            {"icon": "bi-receipt", "label": "Total Billed", "value": f"KSh {invoice_total:,.2f}", "color": "primary"},
            {"icon": "bi-cash-stack", "label": "Total Collected", "value": f"KSh {payment_total:,.2f}", "color": "success"},
            {"icon": "bi-exclamation-triangle", "label": "Outstanding", "value": f"KSh {max(invoice_total - payment_total, 0):,.2f}", "color": "danger"},
            {"icon": "bi-file-text", "label": "Invoices Issued", "value": str(invoices.count()), "color": "info"},
        ],
        "sections": [
            {
                "title": "Payments by Method",
                "icon": "bi-credit-card",
                "headers": ["Method", "Count", "Amount"],
                "rows": [
                    [m["payment_method"].title(), str(m["count"]), f"KSh {m['total']:,.2f}"]
                    for m in by_method
                ] or [["No payments", "-", "-"]],
            },
            {
                "title": "Invoice Status Summary",
                "icon": "bi-pie-chart",
                "headers": ["Status", "Count", "Total"],
                "rows": [
                    [s["status"].title(), str(s["count"]), f"KSh {s['total']:,.2f}"]
                    for s in invoice_status
                ] or [["No invoices", "-", "-"]],
            },
        ],
    }


def _clinical(start_date, end_date):
    from consultation.models import Consultation
    from laboratory.models import LabRequest
    from radiology.models import RadiologyRequest
    from pharmacy.models import PharmacyDispense

    consults = Consultation.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    lab_reqs = LabRequest.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    rad_reqs = RadiologyRequest.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    dispenses = PharmacyDispense.objects.filter(dispensed_at__date__gte=start_date, dispensed_at__date__lte=end_date)

    consult_total = consults.count()
    lab_total = lab_reqs.count()
    rad_total = rad_reqs.count()
    dispense_total = dispenses.count()

    by_doctor = list(
        consults.values("doctor__first_name", "doctor__last_name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    by_lab_test = list(
        lab_reqs.values("lab_test__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    by_rad_service = list(
        rad_reqs.values("radiology_service__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    by_medicine = list(
        dispenses.values("medicine__name")
        .annotate(count=Count("id"), qty=Sum("quantity_dispensed"))
        .order_by("-count")[:10]
    )

    return {
        "title": "Clinical Report",
        "cards": [
            {"icon": "bi-chat-dots", "label": "Consultations", "value": str(consult_total), "color": "primary"},
            {"icon": "bi-flask", "label": "Lab Requests", "value": str(lab_total), "color": "info"},
            {"icon": "bi-radioactive", "label": "Radiology", "value": str(rad_total), "color": "warning"},
            {"icon": "bi-capsule", "label": "Pharmacy Dispenses", "value": str(dispense_total), "color": "success"},
        ],
        "sections": [
            {
                "title": "Top Doctors by Consultations",
                "icon": "bi-person-badge",
                "headers": ["Doctor", "Count"],
                "rows": [
                    [f"{d['doctor__first_name']} {d['doctor__last_name']}", str(d["count"])]
                    for d in by_doctor
                ] or [["No consultations", "-"]],
            },
            {
                "title": "Top 10 Lab Tests Requested",
                "icon": "bi-flask",
                "headers": ["Test", "Requests"],
                "rows": [
                    [t["lab_test__name"], str(t["count"])] for t in by_lab_test
                ] or [["No lab requests", "-"]],
            },
            {
                "title": "Top Radiology Services",
                "icon": "bi-radioactive",
                "headers": ["Service", "Requests"],
                "rows": [
                    [s["radiology_service__name"], str(s["count"])] for s in by_rad_service
                ] or [["No radiology requests", "-"]],
            },
            {
                "title": "Top Dispensed Medicines",
                "icon": "bi-capsule",
                "headers": ["Medicine", "Dispenses", "Qty"],
                "rows": [
                    [m["medicine__name"], str(m["count"]), f"{m['qty']:.0f}"]
                    for m in by_medicine
                ] or [["No dispenses", "-", "-"]],
            },
        ],
    }


def _patients(start_date, end_date):
    from patients.models import Patient
    from triage.models import Visit
    from admission.models import Admission

    patients = Patient.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    visits = Visit.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    admissions = Admission.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

    visit_statuses = list(
        visits.values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )

    admitted = admissions.count()
    discharged = admissions.filter(status=Admission.Status.DISCHARGED).count()

    avg_stay = None
    discharged_adms = admissions.filter(
        status=Admission.Status.DISCHARGED,
        discharge_date__isnull=False,
        admission_date__isnull=False,
    )
    if discharged_adms.exists():
        days = sum((a.discharge_date - a.admission_date).days for a in discharged_adms)
        avg_stay = round(days / discharged_adms.count(), 1)

    return {
        "title": "Patients & Visits Report",
        "cards": [
            {"icon": "bi-person-plus", "label": "New Patients", "value": str(patients.count()), "color": "primary"},
            {"icon": "bi-arrow-right-circle", "label": "Total Visits", "value": str(visits.count()), "color": "info"},
            {"icon": "bi-hospital", "label": "Admissions", "value": str(admitted), "color": "warning"},
            {"icon": "bi-box-arrow-right", "label": "Discharges", "value": str(discharged), "color": "success"},
        ],
        "sections": [
            {
                "title": "Visits by Status",
                "icon": "bi-pie-chart",
                "headers": ["Status", "Count"],
                "rows": [
                    [s["status"].title(), str(s["count"])] for s in visit_statuses
                ] or [["No visits", "-"]],
            },
            {
                "title": "Average Length of Stay",
                "icon": "bi-clock-history",
                "headers": ["Metric", "Value"],
                "rows": [
                    ["Avg Stay (days)", str(avg_stay) if avg_stay else "N/A"],
                    ["Total Discharged", str(discharged)],
                ],
            },
        ],
    }


def _inventory(start_date=None, end_date=None):
    from inventory.models import Medicine, Stock

    medicines = Medicine.objects.filter(is_active=True)
    total = medicines.count()

    low_stock = list(
        medicines.annotate(total_stock=Sum("stocks__quantity"))
        .filter(Q(total_stock__lt=10) | Q(total_stock__isnull=True))
        .order_by("name")[:20]
    )

    expiring = list(
        Stock.objects.filter(
            expiry_date__gte=date.today(),
            expiry_date__lte=date.today() + timedelta(days=30),
            quantity__gt=0,
        ).select_related("medicine").order_by("expiry_date")[:20]
    )

    return {
        "title": "Inventory Report",
        "cards": [
            {"icon": "bi-box-seam", "label": "Active Medicines", "value": str(total), "color": "primary"},
            {"icon": "bi-exclamation-triangle", "label": "Low Stock Items", "value": str(len(low_stock)), "color": "danger"},
            {"icon": "bi-clock-history", "label": "Expiring in 30 Days", "value": str(len(expiring)), "color": "warning"},
            {"icon": "bi-calculator", "label": "Total Stock Units", "value": str(Stock.objects.aggregate(t=Sum("quantity"))["t"] or 0), "color": "info"},
        ],
        "sections": [
            {
                "title": "Low Stock Items",
                "icon": "bi-exclamation-triangle",
                "headers": ["Medicine", "Total Stock"],
                "rows": [
                    [m.name, f"{m.total_stock or 0:.0f}"]
                    for m in low_stock
                ] or [["All items well-stocked", "-"]],
            },
            {
                "title": "Expiring Soon",
                "icon": "bi-clock-history",
                "headers": ["Medicine", "Batch", "Qty", "Expiry"],
                "rows": [
                    [s.medicine.name, s.batch_number, f"{s.quantity:.0f}", s.expiry_date.strftime("%b %d, %Y")]
                    for s in expiring
                ] or [["No expiring stock", "-", "-", "-"]],
            },
        ],
    }
