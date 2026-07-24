"""
Tests for the Consultation module.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from triage.models import Visit
from patients.models import Patient, PatientCategory
from inventory.models import Medicine, MedicineCategory
from consultation import services
from consultation.models import Consultation, Prescription

User = get_user_model()


class ConsultationModelTest(TestCase):
    """Test Consultation and Prescription models."""

    def setUp(self):
        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.user = User.objects.create_user(
            username="doctor1", email="doc@test.com", first_name="John", last_name="Doe",
            password="testpass", role="Doctor",
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
            status=Visit.Status.WAITING_DOCTOR,
        )
        self.med_cat = MedicineCategory.objects.create(name="Antibiotics")
        self.medicine = Medicine.objects.create(
            name="Amoxicillin", category=self.med_cat, dosage_form="TABLET",
            strength="500mg", unit="pcs", selling_price=Decimal("50"),
            minimum_stock=10, reorder_level=20,
        )

    def test_consultation_str(self):
        consultation = Consultation.objects.create(visit=self.visit, doctor=self.user)
        self.assertIn("VIS-2026-000001", str(consultation))

    def test_consultation_default_status(self):
        consultation = Consultation.objects.create(visit=self.visit, doctor=self.user)
        self.assertEqual(consultation.status, Consultation.Status.IN_PROGRESS)

    def test_prescription_str(self):
        consultation = Consultation.objects.create(visit=self.visit, doctor=self.user)
        rx = Prescription.objects.create(
            consultation=consultation, medicine=self.medicine,
            dosage="500", dosage_unit="MG", frequency="3 times daily",
            duration_days=7, quantity=21,
        )
        self.assertIn("Amoxicillin", str(rx))

    def test_consultation_default_fee(self):
        consultation = Consultation.objects.create(visit=self.visit, doctor=self.user)
        self.assertEqual(consultation.consultation_fee, Decimal("50"))


class ConsultationServicesTest(TestCase):
    """Test consultation service layer."""

    def setUp(self):
        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.user = User.objects.create_user(
            username="doctor2", email="doc@test.com", first_name="John", last_name="Doe",
            password="testpass", role="Doctor",
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
            status=Visit.Status.WAITING_DOCTOR,
        )
        self.med_cat = MedicineCategory.objects.create(name="Antibiotics")
        self.medicine = Medicine.objects.create(
            name="Amoxicillin", category=self.med_cat, dosage_form="TABLET",
            strength="500mg", unit="pcs", selling_price=Decimal("50"),
            minimum_stock=10, reorder_level=20,
        )

    def test_get_doctor_queue(self):
        queue = services.get_doctor_queue()
        self.assertEqual(queue.count(), 1)

    def test_get_doctor_queue_excludes_other_statuses(self):
        Visit.objects.create(
            patient=self.patient, visit_number="VIS-2026-000002",
            status=Visit.Status.WAITING_TRIAGE,
        )
        queue = services.get_doctor_queue()
        self.assertEqual(queue.count(), 1)

    def test_start_consultation(self):
        consultation = services.start_consultation(self.visit.pk, self.user)
        self.assertEqual(consultation.visit.pk, self.visit.pk)
        self.assertEqual(consultation.doctor, self.user)
        self.assertEqual(consultation.status, Consultation.Status.IN_PROGRESS)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, Visit.Status.IN_CONSULTATION)

    def test_start_consultation_wrong_status_raises(self):
        self.visit.status = Visit.Status.WAITING_TRIAGE
        self.visit.save()
        with self.assertRaises(ValueError):
            services.start_consultation(self.visit.pk, self.user)

    def test_complete_consultation_no_prescriptions(self):
        consultation = services.start_consultation(self.visit.pk, self.user)
        form_data = {
            "diagnosis": "Malaria",
            "notes": "Patient presents with fever.",
            "treatment_plan": "Rest and hydration.",
            "consultation_fee": Decimal("50"),
        }
        result = services.complete_consultation(
            consultation_id=consultation.pk,
            form_data=form_data,
            prescriptions_data=[],
            doctor=self.user,
        )
        self.assertEqual(result.status, Consultation.Status.COMPLETED)
        self.assertIsNotNone(result.completed_at)
        # Visit should be COMPLETED (no labs, no prescriptions)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, Visit.Status.COMPLETED)

    def test_complete_consultation_with_prescriptions(self):
        consultation = services.start_consultation(self.visit.pk, self.user)
        form_data = {
            "diagnosis": "Infection",
            "notes": "Prescribed antibiotics.",
            "treatment_plan": "Finish full course.",
            "consultation_fee": Decimal("50"),
        }
        prescriptions_data = [{
            "medicine_id": self.medicine.pk,
            "dosage": "500",
            "dosage_unit": "MG",
            "frequency": "3 times daily",
            "duration_days": 7,
            "quantity": 21,
            "route": "Oral",
            "instructions": "After meals",
        }]
        result = services.complete_consultation(
            consultation_id=consultation.pk,
            form_data=form_data,
            prescriptions_data=prescriptions_data,
            doctor=self.user,
        )
        self.assertEqual(result.status, Consultation.Status.COMPLETED)
        self.assertEqual(result.prescriptions.count(), 1)
        # Visit should be WAITING_PHARMACY
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, Visit.Status.WAITING_PHARMACY)

    def test_complete_consultation_creates_invoice(self):
        from billing.models import Invoice
        consultation = services.start_consultation(self.visit.pk, self.user)
        form_data = {
            "diagnosis": "Checkup",
            "notes": "",
            "treatment_plan": "",
            "consultation_fee": Decimal("100"),
        }
        services.complete_consultation(
            consultation_id=consultation.pk,
            form_data=form_data,
            prescriptions_data=[],
            doctor=self.user,
        )
        # Verify invoice was created with consultation fee
        invoices = Invoice.objects.filter(visit=self.visit)
        self.assertEqual(invoices.count(), 1)
        self.assertGreaterEqual(invoices.first().total_amount, Decimal("100"))

    def test_cancel_consultation(self):
        consultation = services.start_consultation(self.visit.pk, self.user)
        services.cancel_consultation(consultation.pk)
        consultation.refresh_from_db()
        self.assertEqual(consultation.status, Consultation.Status.CANCELLED)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, Visit.Status.WAITING_DOCTOR)

    def test_get_consultation_stats(self):
        stats = services.get_consultation_stats()
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["completed"], 0)
        self.assertEqual(stats["in_progress"], 0)

        # Start and complete one
        c = services.start_consultation(self.visit.pk, self.user)
        form_data = {
            "diagnosis": "Test",
            "notes": "",
            "treatment_plan": "",
            "consultation_fee": Decimal("50"),
        }
        services.complete_consultation(c.pk, form_data, [], self.user)
        stats = services.get_consultation_stats()
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["completed"], 1)


class ConsultationViewsTest(TestCase):
    """Test consultation views via Django test client."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="doctor3", email="doc@test.com", first_name="Jane", last_name="Doe",
            password="testpass", role="Doctor",
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
            status=Visit.Status.WAITING_DOCTOR,
        )
        self.client.login(username="doctor3", password="testpass")

    def test_doctor_queue_view(self):
        resp = self.client.get("/consultation/")
        self.assertEqual(resp.status_code, 200)

    def test_start_consultation_view(self):
        resp = self.client.post(f"/consultation/start/{self.visit.pk}/")
        self.assertEqual(resp.status_code, 302)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, Visit.Status.IN_CONSULTATION)

    def test_conduct_consultation_view_get(self):
        consultation = services.start_consultation(self.visit.pk, self.user)
        resp = self.client.get(f"/consultation/{consultation.pk}/conduct/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Prescription")

    def test_conduct_consultation_view_post(self):
        consultation = services.start_consultation(self.visit.pk, self.user)
        resp = self.client.post(f"/consultation/{consultation.pk}/conduct/", {
            "diagnosis": "Malaria",
            "notes": "High fever",
            "treatment_plan": "Medication",
            "consultation_fee": "50",
            "prescriptions-TOTAL_FORMS": "1",
            "prescriptions-INITIAL_FORMS": "0",
            "prescriptions-MIN_NUM_FORMS": "0",
            "prescriptions-MAX_NUM_FORMS": "10",
            "prescriptions-0-medicine": self._create_medicine().pk,
            "prescriptions-0-dosage": "500",
            "prescriptions-0-dosage_unit": "MG",
            "prescriptions-0-frequency": "3 times daily",
            "prescriptions-0-duration_days": "7",
            "prescriptions-0-quantity": "21",
            "prescriptions-0-route": "Oral",
        })
        self.assertEqual(resp.status_code, 302)
        consultation.refresh_from_db()
        self.assertEqual(consultation.status, Consultation.Status.COMPLETED)

    def _create_medicine(self):
        cat = MedicineCategory.objects.create(name="Analgesics")
        return Medicine.objects.create(
            name="Paracetamol", category=cat, dosage_form="TABLET",
            strength="500mg", unit="pcs", selling_price=Decimal("30"),
            minimum_stock=10, reorder_level=20,
        )

    def test_consultation_detail_view(self):
        consultation = services.start_consultation(self.visit.pk, self.user)
        form_data = {
            "diagnosis": "Test",
            "notes": "",
            "treatment_plan": "",
            "consultation_fee": Decimal("50"),
        }
        services.complete_consultation(consultation.pk, form_data, [], self.user)
        resp = self.client.get(f"/consultation/{consultation.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test")
