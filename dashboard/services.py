"""
Service layer for dashboard app.
Aggregates stats from all other modules.
"""
from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone


def get_dashboard_context(user):
    """
    Get all dashboard data for the given user.
    Returns a dict with stats, charts data, and recent activity.
    """
    context = {}

    # ─── Patient Stats ───────────────────────────────────────────────
    from patients.models import Patient
    context["total_patients"] = Patient.objects.filter(is_active=True).count()
    today = date.today()
    context["patients_today"] = Patient.objects.filter(created_at__date=today).count()

    # ─── Visit Stats ─────────────────────────────────────────────────
    from triage.models import Visit
    visits_base = Visit.objects
    context["total_visits"] = visits_base.count()
    context["visits_today"] = visits_base.filter(visit_date=today).count()
    context["waiting_triage"] = visits_base.filter(status=Visit.Status.WAITING_TRIAGE).count()
    context["waiting_doctor"] = visits_base.filter(status=Visit.Status.WAITING_DOCTOR).count()
    context["waiting_pharmacy"] = visits_base.filter(status=Visit.Status.WAITING_PHARMACY).count()
    context["waiting_lab"] = visits_base.filter(status=Visit.Status.WAITING_LAB).count()
    context["waiting_xray"] = visits_base.filter(status=Visit.Status.WAITING_XRAY).count()
    context["waiting_ultrasound"] = visits_base.filter(status=Visit.Status.WAITING_ULTRASOUND).count()
    context["waiting_doctor_review"] = visits_base.filter(status=Visit.Status.WAITING_DOCTOR_REVIEW).count()

    # ─── Consultation Stats ──────────────────────────────────────────
    from consultation.models import Consultation
    context["consultations_today"] = Consultation.objects.filter(
        created_at__date=today,
    ).count()
    context["consultations_pending"] = Consultation.objects.filter(
        status=Consultation.Status.IN_PROGRESS,
    ).count()

    # ─── Admission Stats ─────────────────────────────────────────────
    from admission.models import Admission
    context["admitted_patients"] = Admission.objects.filter(
        status=Admission.Status.ADMITTED,
    ).count()
    context["discharged_today"] = Admission.objects.filter(
        status=Admission.Status.DISCHARGED,
        discharge_date=today,
    ).count()
    from admission.models import Bed
    total_beds = Bed.objects.count()
    occupied_beds = Bed.objects.filter(is_occupied=True).count()
    context["bed_occupancy"] = f"{occupied_beds}/{total_beds}"
    context["bed_occupancy_pct"] = round(
        (occupied_beds / total_beds * 100) if total_beds else 0, 1
    )

    # ─── Lab Stats ───────────────────────────────────────────────────
    from laboratory.models import LabRequest
    context["lab_pending"] = LabRequest.objects.filter(is_completed=False).count()
    context["lab_completed_today"] = LabRequest.objects.filter(
        is_completed=True, completed_at__date=today,
    ).count()

    # ─── Radiology Stats ─────────────────────────────────────────────
    from radiology.models import RadiologyRequest
    context["radiology_pending"] = RadiologyRequest.objects.filter(is_completed=False).count()
    context["radiology_completed_today"] = RadiologyRequest.objects.filter(
        is_completed=True, completed_at__date=today,
    ).count()

    # ─── Pharmacy Stats ──────────────────────────────────────────────
    from pharmacy.models import PharmacyDispense
    context["dispenses_today"] = PharmacyDispense.objects.filter(
        dispensed_at__date=today,
    ).count()

    # ─── Inventory Stats ─────────────────────────────────────────────
    from inventory.models import Medicine, Stock
    context["total_medicines"] = Medicine.objects.filter(is_active=True).count()
    low_stock = Medicine.objects.filter(is_active=True).annotate(
        total_stock=Sum("stocks__quantity"),
    ).filter(
        Q(total_stock__lt=10) | Q(total_stock__isnull=True),
    )
    context["low_stock_count"] = low_stock.count()
    context["expiring_medicines"] = Stock.objects.filter(
        expiry_date__gte=today,
        expiry_date__lte=today + timedelta(days=30),
        quantity__gt=0,
    ).count()

    # ─── Billing Stats ───────────────────────────────────────────────
    from billing.models import Invoice
    invoices_query = Invoice.objects
    total_revenue = invoices_query.aggregate(
        total=Sum("total_amount"),
    )["total"] or 0
    total_collected = invoices_query.aggregate(
        total=Sum("amount_paid"),
    )["total"] or 0
    context["total_outstanding"] = Decimal(str(total_revenue)) - Decimal(str(total_collected))
    context["pending_invoices"] = invoices_query.filter(status=Invoice.Status.PENDING).count()
    context["paid_today"] = invoices_query.filter(
        status=Invoice.Status.PAID,
        updated_at__date=today,
    ).count()

    # ─── Revenue Today (from payments) ───────────────────────────────
    from cashier.models import Payment
    revenue_today = Payment.objects.filter(
        created_at__date=today,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    context["revenue_today"] = revenue_today

    # ─── Visit Status Distribution (for Chart.js pie) ────────────────
    status_counts = visits_base.values("status").annotate(count=Count("id"))
    context["visit_status_labels"] = []
    context["visit_status_data"] = []
    status_labels = dict(Visit.Status.choices)
    for item in status_counts:
        context["visit_status_labels"].append(status_labels.get(item["status"], item["status"]))
        context["visit_status_data"].append(item["count"])

    # ─── Weekly Visit Trend (for Chart.js line) ──────────────────────
    week_ago = today - timedelta(days=6)
    weekly_labels = []
    weekly_data = []
    for i in range(7):
        day = week_ago + timedelta(days=i)
        weekly_labels.append(day.strftime("%a"))
        weekly_data.append(
            Visit.objects.filter(visit_date=day).count()
        )
    context["weekly_labels"] = weekly_labels
    context["weekly_visits"] = weekly_data

    # ─── Revenue Trend (last 7 days) ─────────────────────────────────
    weekly_revenue = []
    for i in range(7):
        day = week_ago + timedelta(days=i)
        weekly_revenue.append(
            float(Payment.objects.filter(created_at__date=day).aggregate(
                total=Sum("amount"),
            )["total"] or 0)
        )
    context["weekly_revenue"] = weekly_revenue

    # ─── Recent Activity ─────────────────────────────────────────────
    recent = []
    # Recent patients
    for p in Patient.objects.order_by("-created_at")[:5]:
        recent.append({
            "icon": "bi-person-plus",
            "color": "primary",
            "text": f"New patient: {p.full_name}",
            "time": p.created_at,
        })
    # Recent visits
    for v in Visit.objects.select_related("patient").order_by("-created_at")[:5]:
        recent.append({
            "icon": "bi-arrow-right-circle",
            "color": "info",
            "text": f"Visit {v.visit_number} - {v.patient.full_name} ({v.get_status_display()})",
            "time": v.created_at,
        })
    # Recent pharmacy dispenses
    for d in PharmacyDispense.objects.select_related("medicine").order_by("-dispensed_at")[:5]:
        recent.append({
            "icon": "bi-capsule",
            "color": "success",
            "text": f"Dispensed {d.medicine.name} x{d.quantity_dispensed}",
            "time": d.dispensed_at,
        })
    recent.sort(key=lambda x: x["time"], reverse=True)
    context["recent_activities"] = recent[:10]

    # ─── Role-specific contextual data ───────────────────────────────
    role = user.role
    if role in ("DOCTOR",):
        context["my_pending_consultations"] = Consultation.objects.filter(
            doctor=user, status=Consultation.Status.IN_PROGRESS,
        ).count()
    elif role in ("NURSE", "WARD_MANAGER"):
        context["my_admitted_patients"] = Admission.objects.filter(
            status=Admission.Status.ADMITTED,
        ).select_related("patient", "ward", "room", "bed").order_by("-created_at")[:10]
    elif role in ("PHARMACIST",):
        context["my_pending_count"] = Consultation.objects.filter(
            status=Consultation.Status.COMPLETED,
            prescriptions__is_dispensed=False,
        ).distinct().count()
    elif role in ("CASHIER",):
        from cashier.services import get_pending_invoices, get_outstanding_summary
        context["pending_invoices_list"] = get_pending_invoices()[:10]
        context["cashier_summary"] = get_outstanding_summary()

    return context
