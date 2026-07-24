"""
Tests for the Dashboard module.
"""
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from patients.models import Patient, PatientCategory
from triage.models import Visit
from consultation.models import Consultation, Prescription
from inventory.models import Medicine, MedicineCategory
from billing.models import Invoice
from cashier.models import Payment
from admission.models import Ward, Room, Bed, Admission
from laboratory.models import LabTest, LabRequest
from radiology.models import RadiologyService, RadiologyRequest
from pharmacy.models import PharmacyDispense
from dashboard.services import get_dashboard_context

User = get_user_model()


class DashboardServicesTest(TestCase):
    """Test dashboard service layer aggregation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="admin", email="admin@test.com", first_name="Admin", last_name="User",
            password="testpass", role="Admin",
        )
        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.patient = Patient.objects.create(
            patient_number="THH-2026-000001",
            first_name="Jane", last_name="Doe", gender="FEMALE",
            date_of_birth="1990-01-15", phone="08012345678",
            address="Lagos", next_of_kin_name="Jack", next_of_kin_phone="08087654321",
            next_of_kin_relationship="Brother",
            patient_category=self.category, patient_type="NEW", payment_type="CASH",
        )
        self.visit = Visit.objects.create(
            patient=self.patient, visit_number="VIS-2026-000001",
            status=Visit.Status.WAITING_DOCTOR,
        )

    def test_dashboard_context_returns_all_keys(self):
        context = get_dashboard_context(self.user)
        required_keys = [
            "total_patients", "total_visits", "waiting_triage", "waiting_doctor",
            "waiting_pharmacy", "waiting_lab", "waiting_radiology",
            "admitted_patients", "bed_occupancy", "bed_occupancy_pct",
            "lab_pending", "lab_completed_today",
            "radiology_pending", "radiology_completed_today",
            "dispenses_today", "total_medicines", "low_stock_count",
            "revenue_today", "total_outstanding", "pending_invoices",
            "visit_status_labels", "visit_status_data",
            "weekly_labels", "weekly_visits", "weekly_revenue",
            "recent_activities",
        ]
        for key in required_keys:
            self.assertIn(key, context, f"Missing key: {key}")

    def test_dashboard_basic_counts(self):
        context = get_dashboard_context(self.user)
        self.assertEqual(context["total_patients"], 1)
        self.assertEqual(context["total_visits"], 1)
        self.assertEqual(context["waiting_doctor"], 1)

    def test_dashboard_includes_visit_data(self):
        context = get_dashboard_context(self.user)
        self.assertIn("Waiting for Doctor", context["visit_status_labels"])
        self.assertIn(1, context["visit_status_data"])

    def test_dashboard_weekly_data(self):
        context = get_dashboard_context(self.user)
        self.assertEqual(len(context["weekly_labels"]), 7)
        self.assertEqual(len(context["weekly_visits"]), 7)
        self.assertEqual(len(context["weekly_revenue"]), 7)

    def test_dashboard_doctor_role_context(self):
        doctor = User.objects.create_user(
            username="doctor", email="doc@test.com",
            password="testpass", role="DOCTOR",
        )
        Consultation.objects.create(visit=self.visit, doctor=doctor)
        context = get_dashboard_context(doctor)
        self.assertIn("my_pending_consultations", context)

    def test_dashboard_cashier_role_context(self):
        cashier = User.objects.create_user(
            username="cashier", email="cash@test.com",
            password="testpass", role="CASHIER",
        )
        Invoice.objects.create(
            patient=self.patient, visit=self.visit,
            invoice_number="INV-2026-000001",
            total_amount=Decimal("5000"), amount_paid=Decimal("0"),
        )
        context = get_dashboard_context(cashier)
        self.assertIn("pending_invoices_list", context)
        self.assertIn("cashier_summary", context)

    def test_dashboard_nurse_role_context(self):
        nurse = User.objects.create_user(
            username="nurse", email="nurse@test.com",
            password="testpass", role="NURSE",
        )
        ward = Ward.objects.create(name="General Ward", ward_type="GENERAL", price_per_night=Decimal("5000"))
        room = Room.objects.create(room_number="A1", ward=ward, room_type="SHARED")
        bed = Bed.objects.create(bed_number="B1", room=room, is_occupied=True)
        Admission.objects.create(
            patient=self.patient, visit=self.visit,
            ward=ward, room=room, bed=bed,
        )
        context = get_dashboard_context(nurse)
        self.assertIn("my_admitted_patients", context)
        self.assertEqual(len(context["my_admitted_patients"]), 1)

    def test_dashboard_lab_pending_count(self):
        lab_test = LabTest.objects.create(
            name="CBC", category="HAEMATOLOGY", price=Decimal("1500"),
        )
        LabRequest.objects.create(
            visit=self.visit, lab_test=lab_test,
            clinical_indication="Fever",
        )
        context = get_dashboard_context(self.user)
        self.assertEqual(context["lab_pending"], 1)

    def test_dashboard_radiology_pending_count(self):
        service = RadiologyService.objects.create(
            name="Chest X-ray", service_type="XRAY", price=Decimal("3000"),
        )
        RadiologyRequest.objects.create(
            visit=self.visit, radiology_service=service,
            clinical_indication="Cough",
        )
        context = get_dashboard_context(self.user)
        self.assertEqual(context["radiology_pending"], 1)

    def test_dashboard_pharmacy_dispense_count(self):
        med_cat = MedicineCategory.objects.create(name="General")
        medicine = Medicine.objects.create(
            name="Paracetamol", category=med_cat, dosage_form="TABLET",
            strength="500mg", unit="pcs", selling_price=Decimal("30"),
            minimum_stock=10, reorder_level=20,
        )
        PharmacyDispense.objects.create(
            visit=self.visit, medicine=medicine,
            quantity_dispensed=10, charge=Decimal("300"),
            dispensed_by=self.user,
        )
        context = get_dashboard_context(self.user)
        self.assertEqual(context["dispenses_today"], 1)

    def test_dashboard_revenue_today(self):
        invoice = Invoice.objects.create(
            patient=self.patient, visit=self.visit,
            invoice_number="INV-2026-000001",
            total_amount=Decimal("10000"), amount_paid=Decimal("0"),
        )
        Payment.objects.create(
            invoice=invoice, amount=Decimal("5000"),
            payment_method="CASH", receipt_number="RCP-2026-000001",
            received_by=self.user,
        )
        context = get_dashboard_context(self.user)
        self.assertEqual(context["revenue_today"], Decimal("5000"))


class DashboardViewTest(TestCase):
    """Test dashboard view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="admin", email="admin@test.com",
            password="testpass", role="Admin",
        )

    def test_dashboard_requires_login(self):
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 302)

    def test_dashboard_returns_200(self):
        self.client.login(username="admin", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_contains_stats(self):
        self.client.login(username="admin", password="testpass")
        resp = self.client.get("/dashboard/")
        self.assertContains(resp, "Total Patients")
        self.assertContains(resp, "Welcome back")
