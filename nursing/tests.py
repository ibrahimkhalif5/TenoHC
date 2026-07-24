"""
Integration tests for the Nursing module.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from triage.models import Visit
from patients.models import Patient, PatientCategory
from admission.models import Ward, Room, Bed, Admission
from admission import services as admission_services
from nursing.models import NursingNote, DailyVitals, Treatment
from nursing import services

User = get_user_model()


class NursingModelsTest(TestCase):
    """Test nursing models."""

    def setUp(self):
        self.ward = Ward.objects.create(
            name="General Ward", ward_type="GENERAL",
            price_per_night=Decimal("5000.00"),
        )
        self.room = Room.objects.create(ward=self.ward, room_number="G-101", capacity=2)
        self.bed = Bed.objects.create(room=self.room, bed_number="G-101-B1")

        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.nurse = User.objects.create_user(
            username="nurse1", email="nurse@test.com", first_name="Nancy", last_name="Nurse",
            password="testpass", role="Nurse",
        )
        self.patient = Patient.objects.create(
            patient_number="THH-2026-000001",
            first_name="John", last_name="Doe", gender="MALE",
            date_of_birth="1990-01-01", phone="08012345678",
            address="Lagos", next_of_kin_name="Jane", next_of_kin_phone="08087654321",
            next_of_kin_relationship="Wife",
            patient_category=self.category, patient_type="NEW", payment_type="CASH",
        )
        self.visit = Visit.objects.create(
            patient=self.patient, visit_number="VIS-2026-000001",
            status="ADMISSION_IN_PROGRESS",
        )
        self.admission = admission_services.admit_patient(
            visit_id=self.visit.pk, ward_id=self.ward.pk,
            room_id=self.room.pk, bed_id=self.bed.pk,
            user=self.nurse,
        )

    def test_nursing_note_str(self):
        note = NursingNote.objects.create(
            admission=self.admission, note="Patient resting well", created_by=self.nurse,
        )
        self.assertIn("John Doe", str(note))

    def test_daily_vitals_str(self):
        vitals = DailyVitals.objects.create(
            admission=self.admission, temperature=Decimal("36.5"),
            blood_pressure_systolic=120, blood_pressure_diastolic=80,
            pulse=72, respiratory_rate=16, oxygen_saturation=Decimal("98.0"),
            recorded_by=self.nurse,
        )
        self.assertIn("John Doe", str(vitals))

    def test_treatment_str(self):
        treatment = Treatment.objects.create(
            admission=self.admission, treatment="IV Cannulation",
            medication="Paracetamol", dosage="500mg",
            given_by=self.nurse,
        )
        self.assertIn("IV Cannulation", str(treatment))


class NursingServicesTest(TestCase):
    """Test nursing service layer."""

    def setUp(self):
        self.ward = Ward.objects.create(
            name="General Ward", ward_type="GENERAL",
            price_per_night=Decimal("5000.00"),
        )
        self.room = Room.objects.create(ward=self.ward, room_number="G-101", capacity=2)
        self.bed = Bed.objects.create(room=self.room, bed_number="G-101-B1")

        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.nurse = User.objects.create_user(
            username="nurse2", email="nurse@test.com", first_name="Nancy", last_name="Nurse",
            password="testpass", role="Nurse",
        )
        self.patient = Patient.objects.create(
            patient_number="THH-2026-000001",
            first_name="John", last_name="Doe", gender="MALE",
            date_of_birth="1990-01-01", phone="08012345678",
            address="Lagos", next_of_kin_name="Jane", next_of_kin_phone="08087654321",
            next_of_kin_relationship="Wife",
            patient_category=self.category, patient_type="NEW", payment_type="CASH",
        )
        self.visit = Visit.objects.create(
            patient=self.patient, visit_number="VIS-2026-000001",
            status="ADMISSION_IN_PROGRESS",
        )
        self.admission = admission_services.admit_patient(
            visit_id=self.visit.pk, ward_id=self.ward.pk,
            room_id=self.room.pk, bed_id=self.bed.pk,
            user=self.nurse,
        )

    def test_get_admitted_patients(self):
        result = services.get_admitted_patients()
        self.assertEqual(result.count(), 1)

    def test_get_admission_detail(self):
        detail = services.get_admission_detail(self.admission.pk)
        self.assertEqual(detail.patient, self.patient)

    def test_add_nursing_note(self):
        note = services.add_nursing_note(self.admission.pk, "Patient resting well", self.nurse)
        self.assertEqual(note.note, "Patient resting well")
        self.assertEqual(note.created_by, self.nurse)
        self.assertEqual(self.admission.nursing_notes.count(), 1)

    def test_add_daily_vitals(self):
        data = {
            "temperature": Decimal("36.5"),
            "blood_pressure_systolic": 120,
            "blood_pressure_diastolic": 80,
            "pulse": 72,
            "respiratory_rate": 16,
            "oxygen_saturation": Decimal("98.0"),
            "weight": Decimal("70.0"),
            "notes": "Patient comfortable",
        }
        vitals = services.add_daily_vitals(self.admission.pk, data, self.nurse)
        self.assertEqual(vitals.pulse, 72)
        self.assertEqual(vitals.weight, Decimal("70.0"))
        self.assertEqual(self.admission.daily_vitals.count(), 1)

    def test_add_treatment(self):
        data = {
            "treatment": "IV Cannulation",
            "medication": "Paracetamol",
            "dosage": "500mg",
            "frequency": "Twice daily",
            "notes": "Administered with food",
        }
        treatment = services.add_treatment(self.admission.pk, data, self.nurse)
        self.assertEqual(treatment.treatment, "IV Cannulation")
        self.assertEqual(treatment.medication, "Paracetamol")
        self.assertEqual(self.admission.treatments.count(), 1)


class NursingViewsTest(TestCase):
    """Test nursing views via Django test client."""

    def setUp(self):
        self.client = Client()
        self.nurse = User.objects.create_user(
            username="nurse3", email="nurse@test.com", first_name="Nancy", last_name="Nurse",
            password="testpass", role="Nurse",
        )
        self.ward = Ward.objects.create(
            name="General Ward", ward_type="GENERAL",
            price_per_night=Decimal("5000.00"),
        )
        self.room = Room.objects.create(ward=self.ward, room_number="G-101", capacity=2)
        self.bed = Bed.objects.create(room=self.room, bed_number="G-101-B1")

        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.patient = Patient.objects.create(
            patient_number="THH-2026-000001",
            first_name="John", last_name="Doe", gender="MALE",
            date_of_birth="1990-01-01", phone="08012345678",
            address="Lagos", next_of_kin_name="Jane", next_of_kin_phone="08087654321",
            next_of_kin_relationship="Wife",
            patient_category=self.category, patient_type="NEW", payment_type="CASH",
        )
        self.visit = Visit.objects.create(
            patient=self.patient, visit_number="VIS-2026-000001",
            status="ADMISSION_IN_PROGRESS",
        )
        self.admission = admission_services.admit_patient(
            visit_id=self.visit.pk, ward_id=self.ward.pk,
            room_id=self.room.pk, bed_id=self.bed.pk,
            user=self.nurse,
        )
        self.client.login(username="nurse3", password="testpass")

    def test_patient_list_view(self):
        resp = self.client.get("/nursing/")
        self.assertEqual(resp.status_code, 200)

    def test_patient_detail_view(self):
        resp = self.client.get(f"/nursing/{self.admission.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_add_nursing_note_view(self):
        resp = self.client.post(f"/nursing/{self.admission.pk}/note/", {
            "note": "Patient resting well",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.admission.nursing_notes.count(), 1)

    def test_add_daily_vitals_view(self):
        resp = self.client.post(f"/nursing/{self.admission.pk}/vitals/", {
            "temperature": "36.5",
            "blood_pressure_systolic": "120",
            "blood_pressure_diastolic": "80",
            "pulse": "72",
            "respiratory_rate": "16",
            "oxygen_saturation": "98.0",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.admission.daily_vitals.count(), 1)

    def test_add_treatment_view(self):
        resp = self.client.post(f"/nursing/{self.admission.pk}/treatment/", {
            "treatment": "IV Cannulation",
            "medication": "Paracetamol",
            "dosage": "500mg",
            "frequency": "Twice daily",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.admission.treatments.count(), 1)

    def test_add_note_empty(self):
        resp = self.client.post(f"/nursing/{self.admission.pk}/note/", {
            "note": "",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.admission.nursing_notes.count(), 0)
