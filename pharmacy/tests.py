"""
Tests for the Pharmacy module.
"""
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from triage.models import Visit
from patients.models import Patient, PatientCategory
from consultation.models import Consultation, Prescription
from inventory.models import Medicine, MedicineCategory, Stock, StockMovement
from pharmacy.models import PharmacyDispense
from pharmacy import services
from billing.models import Invoice
from billing import services as billing_services

User = get_user_model()


class PharmacyServicesTest(TestCase):
    """Test pharmacy service layer."""

    def setUp(self):
        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.doctor = User.objects.create_user(
            username="doctor", email="doc@test.com", first_name="Doc", last_name="Tor",
            password="testpass", role="Doctor",
        )
        self.pharmacist = User.objects.create_user(
            username="pharmacist", email="pharm@test.com", first_name="Pharm", last_name="Acist",
            password="testpass", role="Pharmacist",
        )
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
            status=Visit.Status.WAITING_PHARMACY,
        )
        self.med_cat = MedicineCategory.objects.create(name="Antibiotics")
        self.medicine = Medicine.objects.create(
            name="Amoxicillin", category=self.med_cat, dosage_form="TABLET",
            strength="500mg", unit="pcs", selling_price=Decimal("50"),
            cost_price=Decimal("30"), minimum_stock=10, reorder_level=20,
        )
        # Create stock batch for dispensing
        self.stock = Stock.objects.create(
            medicine=self.medicine, batch_number="BATCH001",
            quantity=100, expiry_date=date.today() + timedelta(days=365),
            purchase_price=Decimal("30"),
        )
        # Create a completed consultation with prescription
        self.consultation = Consultation.objects.create(
            visit=self.visit, doctor=self.doctor,
            diagnosis="Infection", status=Consultation.Status.COMPLETED,
            completed_at=date.today(),
        )
        self.prescription = Prescription.objects.create(
            consultation=self.consultation, medicine=self.medicine,
            dosage="500", dosage_unit="MG", frequency="3 times daily",
            duration_days=7, quantity=21,
        )

    def test_get_pharmacy_queue(self):
        queue = services.get_pharmacy_queue()
        self.assertEqual(queue.count(), 1)

    def test_undispensed_prescriptions(self):
        pending = services.get_undispensed_prescriptions(self.visit.pk)
        self.assertEqual(pending.count(), 1)
        self.assertEqual(pending.first(), self.prescription)

    def test_dispense_prescription(self):
        dispense = services.dispense_prescription(
            prescription_id=self.prescription.pk,
            user=self.pharmacist,
        )
        self.assertIsNotNone(dispense)
        self.assertEqual(dispense.quantity_dispensed, Decimal("21"))
        self.assertEqual(dispense.charge, Decimal("1050"))  # 21 x 50
        self.assertEqual(dispense.dispensed_by, self.pharmacist)
        self.assertEqual(dispense.visit, self.visit)

        # Prescription marked as dispensed
        self.prescription.refresh_from_db()
        self.assertTrue(self.prescription.is_dispensed)

        # Stock decreased
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 79)

        # Invoice created with pharmacy item
        invoice = Invoice.objects.get(visit=self.visit)
        self.assertGreaterEqual(invoice.total_amount, Decimal("1050"))

        # Visit status should remain WAITING_PHARMACY (we only auto-complete on dispense_all)

    def test_dispense_all_pending(self):
        # Add a second prescription
        med2 = Medicine.objects.create(
            name="Paracetamol", category=self.med_cat, dosage_form="TABLET",
            strength="500mg", unit="pcs", selling_price=Decimal("30"),
            cost_price=Decimal("15"), minimum_stock=10, reorder_level=20,
        )
        Stock.objects.create(
            medicine=med2, batch_number="BATCH002",
            quantity=100, expiry_date=date.today() + timedelta(days=365),
            purchase_price=Decimal("15"),
        )
        Prescription.objects.create(
            consultation=self.consultation, medicine=med2,
            dosage="1000", dosage_unit="MG", frequency="2 times daily",
            duration_days=5, quantity=10,
        )

        results = services.dispense_all_pending(self.visit.pk, self.pharmacist)
        self.assertEqual(len(results), 2)

        # Visit should be COMPLETED (no more pending prescriptions)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, Visit.Status.COMPLETED)

    def test_dispense_already_dispensed_raises(self):
        services.dispense_prescription(self.prescription.pk, self.pharmacist)
        with self.assertRaises(ValueError):
            services.dispense_prescription(self.prescription.pk, self.pharmacist)

    def test_dispense_insufficient_stock_raises(self):
        # Set stock to 5, prescription needs 21
        self.stock.quantity = 5
        self.stock.save()
        with self.assertRaises(ValueError):
            services.dispense_prescription(self.prescription.pk, self.pharmacist)

    def test_get_pharmacy_stats(self):
        stats = services.get_pharmacy_stats()
        self.assertEqual(stats["total_dispensed_today"], 0)
        self.assertEqual(stats["pending_count"], 1)

        services.dispense_prescription(self.prescription.pk, self.pharmacist)
        stats = services.get_pharmacy_stats()
        self.assertEqual(stats["total_dispensed_today"], 1)
        self.assertEqual(stats["pending_count"], 0)

    def test_dispense_history(self):
        services.dispense_prescription(self.prescription.pk, self.pharmacist)
        history = services.get_dispense_history(self.visit.pk)
        self.assertEqual(history.count(), 1)

    def test_auto_billing_correct_amount(self):
        services.dispense_prescription(self.prescription.pk, self.pharmacist)
        invoice = Invoice.objects.get(visit=self.visit)
        items = invoice.items.all()
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().description, f"Pharmacy: Amoxicillin (500mg)")
        self.assertEqual(items.first().total_price, Decimal("1050"))


class PharmacyViewsTest(TestCase):
    """Test pharmacy views via Django test client."""

    def setUp(self):
        self.client = Client()
        self.doctor = User.objects.create_user(
            username="doctor2", email="doc@test.com", first_name="Doc", last_name="Tor",
            password="testpass", role="Doctor",
        )
        self.pharmacist = User.objects.create_user(
            username="pharmacist2", email="pharm@test.com", first_name="Pharm", last_name="Acist",
            password="testpass", role="Pharmacist",
        )
        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.patient = Patient.objects.create(
            patient_number="THH-2026-000001",
            first_name="Jim", last_name="Doe", gender="MALE",
            date_of_birth="1985-06-15", phone="08012345678",
            address="Lagos", next_of_kin_name="Jill", next_of_kin_phone="08087654321",
            next_of_kin_relationship="Sister",
            patient_category=self.category, patient_type="NEW", payment_type="CASH",
        )
        self.visit = Visit.objects.create(
            patient=self.patient, visit_number="VIS-2026-000001",
            status=Visit.Status.WAITING_PHARMACY,
        )
        self.med_cat = MedicineCategory.objects.create(name="Analgesics")
        self.medicine = Medicine.objects.create(
            name="Paracetamol", category=self.med_cat, dosage_form="TABLET",
            strength="500mg", unit="pcs", selling_price=Decimal("30"),
            cost_price=Decimal("15"), minimum_stock=10, reorder_level=20,
        )
        Stock.objects.create(
            medicine=self.medicine, batch_number="BATCH001",
            quantity=100, expiry_date=date.today() + timedelta(days=365),
            purchase_price=Decimal("15"),
        )
        self.consultation = Consultation.objects.create(
            visit=self.visit, doctor=self.doctor,
            diagnosis="Headache", status=Consultation.Status.COMPLETED,
            completed_at=date.today(),
        )
        self.prescription = Prescription.objects.create(
            consultation=self.consultation, medicine=self.medicine,
            dosage="1000", dosage_unit="MG", frequency="2 times daily",
            duration_days=5, quantity=10,
        )
        self.client.login(username="pharmacist2", password="testpass")

    def test_pharmacy_queue_view(self):
        resp = self.client.get("/pharmacy/")
        self.assertEqual(resp.status_code, 200)

    def test_pharmacy_dispense_view(self):
        resp = self.client.get(f"/pharmacy/{self.visit.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Paracetamol")

    def test_dispense_single(self):
        resp = self.client.post(f"/pharmacy/dispense/{self.prescription.pk}/")
        self.assertEqual(resp.status_code, 302)
        self.prescription.refresh_from_db()
        self.assertTrue(self.prescription.is_dispensed)

    def test_dispense_all(self):
        resp = self.client.post(f"/pharmacy/{self.visit.pk}/dispense-all/")
        self.assertEqual(resp.status_code, 302)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, Visit.Status.COMPLETED)

    def test_already_dispensed_shows_error(self):
        services.dispense_prescription(self.prescription.pk, self.pharmacist)
        resp = self.client.post(f"/pharmacy/dispense/{self.prescription.pk}/")
        self.assertEqual(resp.status_code, 302)

    def test_dispense_history_view(self):
        services.dispense_prescription(self.prescription.pk, self.pharmacist)
        resp = self.client.get(f"/pharmacy/{self.visit.pk}/history/")
        self.assertEqual(resp.status_code, 200)
