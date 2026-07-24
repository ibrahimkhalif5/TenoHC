"""
Integration tests for the Admission module.
"""
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from triage.models import Visit
from patients.models import Patient, PatientCategory
from billing.models import Invoice, InvoiceItem
from admission.models import Ward, Room, Bed, Admission
from admission import services

User = get_user_model()


class AdmissionModelsTest(TestCase):
    """Test admission models."""

    def setUp(self):
        self.ward = Ward.objects.create(
            name="General Ward", ward_type="GENERAL",
            description="Standard ward", price_per_night=Decimal("5000.00"),
        )
        self.room = Room.objects.create(
            ward=self.ward, room_number="G-101", room_type="SHARED", capacity=4,
        )
        self.bed = Bed.objects.create(room=self.room, bed_number="G-101-B1")

        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.user = User.objects.create_user(
            username="adm1", email="adm@test.com", first_name="Jane", last_name="Doe",
            password="testpass", role="Admin",
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

    def test_ward_str(self):
        self.assertEqual(str(self.ward), "General Ward (General Ward)")

    def test_room_str(self):
        self.assertEqual(str(self.room), "Room G-101 - General Ward")

    def test_bed_str(self):
        self.assertEqual(str(self.bed), "Bed G-101-B1 - Room G-101")

    def test_admission_str(self):
        admission = Admission.objects.create(
            patient=self.patient, visit=self.visit,
            ward=self.ward, room=self.room, bed=self.bed,
            admitted_by=self.user,
        )
        self.assertIn("John Doe", str(admission))
        self.assertIn("General Ward", str(admission))

    def test_admission_nights_stayed(self):
        admission = Admission.objects.create(
            patient=self.patient, visit=self.visit,
            ward=self.ward, room=self.room, bed=self.bed,
            admitted_by=self.user,
        )
        self.assertEqual(admission.nights_stayed, 0)

    def test_admission_nights_stayed_discharged(self):
        admission = Admission.objects.create(
            patient=self.patient, visit=self.visit,
            ward=self.ward, room=self.room, bed=self.bed,
            admitted_by=self.user,
            admission_date=date.today() - timedelta(days=3),
            discharge_date=date.today(),
        )
        self.assertEqual(admission.nights_stayed, 3)

    def test_ward_charge(self):
        admission = Admission.objects.create(
            patient=self.patient, visit=self.visit,
            ward=self.ward, room=self.room, bed=self.bed,
            admitted_by=self.user,
            admission_date=date.today() - timedelta(days=2),
            discharge_date=date.today(),
        )
        self.assertEqual(admission.ward_charge, Decimal("10000.00"))


class AdmissionServicesTest(TestCase):
    """Test admission service layer."""

    def setUp(self):
        self.ward = Ward.objects.create(
            name="General Ward", ward_type="GENERAL",
            description="Standard ward", price_per_night=Decimal("5000.00"),
        )
        self.ward2 = Ward.objects.create(
            name="VIP Ward", ward_type="VIP",
            description="VIP ward", price_per_night=Decimal("25000.00"),
        )
        self.room = Room.objects.create(
            ward=self.ward, room_number="G-101", room_type="SHARED", capacity=2,
        )
        self.bed1 = Bed.objects.create(room=self.room, bed_number="G-101-B1")
        self.bed2 = Bed.objects.create(room=self.room, bed_number="G-101-B2")

        self.vip_room = Room.objects.create(
            ward=self.ward2, room_number="V-301", room_type="SINGLE", capacity=1,
        )
        self.vip_bed = Bed.objects.create(room=self.vip_room, bed_number="V-301-B1")

        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.user = User.objects.create_user(
            username="adm2", email="adm@test.com", first_name="Jane", last_name="Doe",
            password="testpass", role="Admin",
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

    def test_get_all_wards(self):
        wards = services.get_all_wards()
        self.assertEqual(wards.count(), 2)

    def test_get_available_rooms(self):
        rooms = services.get_available_rooms(self.ward.pk)
        self.assertEqual(rooms.count(), 1)

    def test_get_available_beds(self):
        beds = services.get_available_beds(self.room.pk)
        self.assertEqual(beds.count(), 2)

    def test_admit_patient(self):
        admission = services.admit_patient(
            visit_id=self.visit.pk,
            ward_id=self.ward.pk,
            room_id=self.room.pk,
            bed_id=self.bed1.pk,
            diagnosis="Pneumonia",
            user=self.user,
        )
        self.assertIsNotNone(admission)
        self.assertEqual(admission.patient, self.patient)
        self.assertEqual(admission.ward, self.ward)
        self.assertEqual(admission.diagnosis, "Pneumonia")
        # Bed should be marked occupied
        self.bed1.refresh_from_db()
        self.assertTrue(self.bed1.is_occupied)
        # Room should be marked occupied
        self.room.refresh_from_db()
        self.assertTrue(self.room.is_occupied)
        # Visit status - admitted patients are completed (out of queue)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, "COMPLETED")
        # No invoice auto-created on admission
        self.assertFalse(Invoice.objects.filter(visit=self.visit).exists())

    def test_admit_patient_marks_bed_occupied(self):
        services.admit_patient(
            self.visit.pk, self.ward.pk, self.room.pk, self.bed1.pk,
            user=self.user,
        )
        self.bed1.refresh_from_db()
        self.assertTrue(self.bed1.is_occupied)
        # Other bed still available
        self.bed2.refresh_from_db()
        self.assertFalse(self.bed2.is_occupied)

    def test_cannot_admit_to_occupied_bed(self):
        services.admit_patient(
            self.visit.pk, self.ward.pk, self.room.pk, self.bed1.pk,
            user=self.user,
        )
        with self.assertRaises(Exception):
            services.admit_patient(
                self.visit.pk, self.ward.pk, self.room.pk, self.bed1.pk,
                user=self.user,
            )

    def test_discharge_patient(self):
        admission = services.admit_patient(
            self.visit.pk, self.ward.pk, self.room.pk, self.bed1.pk,
            user=self.user,
        )
        # Manually set admission_date to 2 days ago for testing
        admission.admission_date = date.today() - timedelta(days=2)
        admission.save(update_fields=["admission_date"])

        discharged, nights, total_charge = services.discharge_patient(
            admission_id=admission.pk, user=self.user,
        )
        self.assertEqual(nights, 2)
        self.assertEqual(total_charge, Decimal("10000.00"))
        # Bed should be freed
        self.bed1.refresh_from_db()
        self.assertFalse(self.bed1.is_occupied)
        # Admission status
        discharged.refresh_from_db()
        self.assertEqual(discharged.status, Admission.Status.DISCHARGED)
        self.assertIsNotNone(discharged.discharge_date)
        # Visit status
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, "DISCHARGED")
        # Invoice has one item: discharge ward charge
        invoice = Invoice.objects.get(visit=self.visit)
        self.assertEqual(invoice.items.count(), 1)

    def test_discharge_frees_room_when_empty(self):
        admission = services.admit_patient(
            self.visit.pk, self.ward.pk, self.room.pk, self.bed1.pk,
            user=self.user,
        )
        admission.admission_date = date.today() - timedelta(days=1)
        admission.save(update_fields=["admission_date"])

        services.discharge_patient(admission.pk, self.user)
        self.room.refresh_from_db()
        self.assertFalse(self.room.is_occupied)

    def test_get_admission_queue(self):
        queue = services.get_admission_queue()
        self.assertEqual(queue.count(), 1)
        self.assertEqual(queue.first(), self.visit)

    def test_get_admitted_patients(self):
        services.admit_patient(
            self.visit.pk, self.ward.pk, self.room.pk, self.bed1.pk,
            user=self.user,
        )
        admitted = services.get_admitted_patients()
        self.assertEqual(admitted.count(), 1)

    def test_ward_available_beds(self):
        self.assertEqual(self.ward.available_beds, 2)
        services.admit_patient(
            self.visit.pk, self.ward.pk, self.room.pk, self.bed1.pk,
            user=self.user,
        )
        self.ward.refresh_from_db()
        self.assertEqual(self.ward.available_beds, 1)

    def test_room_available_beds(self):
        self.assertEqual(self.room.available_beds, 2)
        services.admit_patient(
            self.visit.pk, self.ward.pk, self.room.pk, self.bed1.pk,
            user=self.user,
        )
        self.assertEqual(self.room.available_beds, 1)


class AdmissionViewsTest(TestCase):
    """Test admission views via Django test client."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="adm3", email="adm@test.com", first_name="Jane", last_name="Doe",
            password="testpass", role="Admin",
        )
        self.ward = Ward.objects.create(
            name="General Ward", ward_type="GENERAL",
            description="Standard ward", price_per_night=Decimal("5000.00"),
        )
        self.room = Room.objects.create(
            ward=self.ward, room_number="G-101", room_type="SHARED", capacity=2,
        )
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
        self.client.login(username="adm3", password="testpass")

    def test_queue_view(self):
        resp = self.client.get("/admission/")
        self.assertEqual(resp.status_code, 200)

    def test_admit_view_get(self):
        resp = self.client.get(f"/admission/{self.visit.pk}/admit/")
        self.assertEqual(resp.status_code, 200)

    def test_admit_view_post(self):
        resp = self.client.post(f"/admission/{self.visit.pk}/admit/", {
            "ward_id": self.ward.pk,
            "room_id": self.room.pk,
            "bed_id": self.bed.pk,
            "diagnosis": "Test",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Admission.objects.filter(visit=self.visit).exists())

    def test_discharge_view_get(self):
        admission = services.admit_patient(
            self.visit.pk, self.ward.pk, self.room.pk, self.bed.pk,
            user=self.user,
        )
        resp = self.client.get(f"/admission/{admission.pk}/discharge/")
        self.assertEqual(resp.status_code, 200)

    def test_discharge_view_post(self):
        admission = services.admit_patient(
            self.visit.pk, self.ward.pk, self.room.pk, self.bed.pk,
            user=self.user,
        )
        resp = self.client.post(f"/admission/{admission.pk}/discharge/")
        self.assertEqual(resp.status_code, 302)
        admission.refresh_from_db()
        self.assertEqual(admission.status, Admission.Status.DISCHARGED)

    def test_ward_manage_view(self):
        resp = self.client.get("/admission/wards/")
        self.assertEqual(resp.status_code, 200)

    def test_api_rooms(self):
        resp = self.client.get(f"/admission/api/rooms/?ward_id={self.ward.pk}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)

    def test_api_beds(self):
        resp = self.client.get(f"/admission/api/beds/?room_id={self.room.pk}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)

    def test_api_rooms_empty(self):
        resp = self.client.get("/admission/api/rooms/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_api_beds_empty(self):
        resp = self.client.get("/admission/api/beds/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])
