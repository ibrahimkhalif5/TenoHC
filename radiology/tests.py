"""
Integration tests for the Radiology module.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from triage.models import Visit
from patients.models import Patient, PatientCategory
from billing.models import Invoice, InvoiceItem
from radiology.models import RadiologyService, RadiologyRequest
from radiology import services

User = get_user_model()


class RadiologyModelsTest(TestCase):
    """Test radiology models."""

    def setUp(self):
        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.service = RadiologyService.objects.create(
            name="Chest X-Ray",
            service_type="XRAY",
            body_part="Chest",
            description="Chest radiograph",
            price=Decimal("15000.00"),
        )
        self.user = User.objects.create_user(
            username="rad1", email="rad@test.com", first_name="Jane", last_name="Doe",
            password="testpass", role="Lab Technician",
        )
        self.patient = Patient.objects.create(
            patient_number="THH-2026-000001",
            first_name="John", last_name="Doe", gender="MALE",
            date_of_birth="1990-01-01", phone="08012345678",
            address="Lagos", next_of_kin_name="Jane", next_of_kin_phone="08087654321",
            next_of_kin_relationship="Wife",
            patient_category=self.category, patient_type="OUTPATIENT",
            payment_type="CASH",
        )
        self.visit = Visit.objects.create(
            patient=self.patient,
            visit_number="VIS-2026-000001",
            status="WAITING_XRAY",
        )

    def test_service_str(self):
        self.assertEqual(str(self.service), "Chest X-Ray (X-Ray)")

    def test_request_str(self):
        req = RadiologyRequest.objects.create(
            visit=self.visit, radiology_service=self.service,
            clinical_indication="Chest pain",
            requested_by=self.user,
        )
        self.assertIn("Chest X-Ray", str(req))
        self.assertIn("VIS-2026-000001", str(req))


class RadiologyServicesTest(TestCase):
    """Test radiology service layer."""

    def setUp(self):
        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.service = RadiologyService.objects.create(
            name="Chest X-Ray",
            service_type="XRAY",
            body_part="Chest",
            description="Chest radiograph",
            price=Decimal("15000.00"),
        )
        self.service2 = RadiologyService.objects.create(
            name="Abdominal Ultrasound",
            service_type="ULTRASOUND",
            body_part="Abdomen",
            description="Ultrasound of abdomen",
            price=Decimal("25000.00"),
        )
        self.user = User.objects.create_user(
            username="rad2", email="rad@test.com", first_name="Jane", last_name="Doe",
            password="testpass", role="Lab Technician",
        )
        self.patient = Patient.objects.create(
            patient_number="THH-2026-000001",
            first_name="John", last_name="Doe", gender="MALE",
            date_of_birth="1990-01-01", phone="08012345678",
            address="Lagos", next_of_kin_name="Jane", next_of_kin_phone="08087654321",
            next_of_kin_relationship="Wife",
            patient_category=self.category, patient_type="OUTPATIENT",
            payment_type="CASH",
        )
        self.visit = Visit.objects.create(
            patient=self.patient,
            visit_number="VIS-2026-000001",
            status="WAITING_XRAY",
        )

    def test_get_radiology_queue(self):
        queue = services.get_radiology_queue()
        self.assertEqual(queue.count(), 1)
        self.assertEqual(queue.first(), self.visit)

    def test_get_available_services(self):
        svc = services.get_available_services()
        self.assertEqual(svc.count(), 2)

    def test_create_radiology_request(self):
        req = services.create_radiology_request(
            visit_id=self.visit.pk,
            service_id=self.service.pk,
            clinical_indication="Chest pain, rule out pneumonia",
            priority="ROUTINE",
            user=self.user,
        )
        self.assertIsNotNone(req)
        self.assertEqual(req.visit, self.visit)
        self.assertEqual(req.radiology_service, self.service)
        self.assertEqual(req.clinical_indication, "Chest pain, rule out pneumonia")
        self.assertEqual(req.requested_by, self.user)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, "WAITING_XRAY")
        invoice = Invoice.objects.get(visit=self.visit)
        self.assertEqual(invoice.total_amount, Decimal("15000.00"))
        item = invoice.items.first()
        self.assertIn("Chest X-Ray", item.description)

    def test_create_multiple_requests(self):
        services.create_radiology_request(
            self.visit.pk, self.service.pk, "Chest pain", "ROUTINE", self.user,
        )
        services.create_radiology_request(
            self.visit.pk, self.service2.pk, "Abdominal pain", "URGENT", self.user,
        )
        self.assertEqual(RadiologyRequest.objects.filter(visit=self.visit).count(), 2)
        invoice = Invoice.objects.get(visit=self.visit)
        self.assertEqual(invoice.total_amount, Decimal("40000.00"))

    def test_complete_radiology_request(self):
        req = services.create_radiology_request(
            self.visit.pk, self.service.pk, "Chest pain", "ROUTINE", self.user,
        )
        completed = services.complete_radiology_request(
            request_id=req.pk,
            findings="No acute chest pathology",
            impression="Normal chest X-ray",
            user=self.user,
        )
        self.assertTrue(completed.is_completed)
        self.assertEqual(completed.completed_by, self.user)
        self.assertIsNotNone(completed.completed_at)
        self.assertEqual(completed.findings, "No acute chest pathology")
        self.assertEqual(completed.impression, "Normal chest X-ray")

    def test_finalize_all_radiology_requests(self):
        services.create_radiology_request(
            self.visit.pk, self.service.pk, "Chest pain", "ROUTINE", self.user,
        )
        services.create_radiology_request(
            self.visit.pk, self.service2.pk, "Abdominal pain", "URGENT", self.user,
        )
        visit, count = services.finalize_all_radiology_requests(self.visit.pk, self.user)
        self.assertEqual(count, 2)
        visit.refresh_from_db()
        self.assertEqual(visit.status, "WAITING_DOCTOR_REVIEW")
        self.assertFalse(RadiologyRequest.objects.filter(visit=self.visit, is_completed=False).exists())

    def test_remove_radiology_request(self):
        req = services.create_radiology_request(
            self.visit.pk, self.service.pk, "Chest pain", "ROUTINE", self.user,
        )
        services.remove_radiology_request(req.pk)
        self.assertEqual(RadiologyRequest.objects.filter(visit=self.visit).count(), 0)
        self.assertFalse(InvoiceItem.objects.filter(
            invoice__visit=self.visit, description__contains="Chest X-Ray",
        ).exists())

    def test_get_visit_radiology_requests(self):
        services.create_radiology_request(
            self.visit.pk, self.service.pk, "Chest pain", "ROUTINE", self.user,
        )
        visit = services.get_visit_radiology_requests(self.visit.pk)
        self.assertEqual(visit.radiology_requests.count(), 1)


class RadiologyViewsTest(TestCase):
    """Test radiology views via Django test client."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="rad3", email="rad@test.com", first_name="Jane", last_name="Doe",
            password="testpass", role="Lab Technician",
        )
        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.service = RadiologyService.objects.create(
            name="Chest X-Ray",
            service_type="XRAY",
            body_part="Chest",
            description="Chest radiograph",
            price=Decimal("15000.00"),
        )
        self.patient = Patient.objects.create(
            patient_number="THH-2026-000001",
            first_name="John", last_name="Doe", gender="MALE",
            date_of_birth="1990-01-01", phone="08012345678",
            address="Lagos", next_of_kin_name="Jane", next_of_kin_phone="08087654321",
            next_of_kin_relationship="Wife",
            patient_category=self.category, patient_type="OUTPATIENT",
            payment_type="CASH",
        )
        self.visit = Visit.objects.create(
            patient=self.patient,
            visit_number="VIS-2026-000001",
            status="WAITING_XRAY",
        )
        self.client.login(username="rad3", password="testpass")

    def test_queue_view(self):
        resp = self.client.get("/radiology/")
        self.assertEqual(resp.status_code, 200)

    def test_detail_view(self):
        resp = self.client.get(f"/radiology/{self.visit.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_submit_result_view(self):
        req = RadiologyRequest.objects.create(
            visit=self.visit, radiology_service=self.service,
            clinical_indication="Chest pain",
            requested_by=self.user,
        )
        resp = self.client.post(f"/radiology/{self.visit.pk}/result/{req.pk}/", {
            "findings": "Normal chest",
            "impression": "No pathology",
        })
        self.assertEqual(resp.status_code, 302)
        req.refresh_from_db()
        self.assertTrue(req.is_completed)
        self.assertEqual(req.findings, "Normal chest")

    def test_complete_all_view(self):
        RadiologyRequest.objects.create(
            visit=self.visit, radiology_service=self.service,
            clinical_indication="Chest pain",
            requested_by=self.user,
        )
        resp = self.client.post(f"/radiology/{self.visit.pk}/complete/")
        self.assertEqual(resp.status_code, 302)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, "WAITING_DOCTOR_REVIEW")

    def test_save_draft_view(self):
        RadiologyRequest.objects.create(
            visit=self.visit, radiology_service=self.service,
            clinical_indication="Chest pain",
            requested_by=self.user,
        )
        resp = self.client.post(f"/radiology/{self.visit.pk}/draft/", {
            "findings_1": "Some draft findings",
            "impression_1": "Some impression",
        })
        self.assertEqual(resp.status_code, 302)

    def test_queue_empty(self):
        Visit.objects.filter(pk=self.visit.pk).delete()
        resp = self.client.get("/radiology/")
        self.assertEqual(resp.status_code, 200)
