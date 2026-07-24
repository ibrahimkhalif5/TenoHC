"""
Integration tests for the Billing + Cashier modules.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from triage.models import Visit
from patients.models import Patient, PatientCategory
from billing.models import Invoice, InvoiceItem
from billing import services as billing_services
from cashier.models import Payment
from cashier import services as cashier_services

User = get_user_model()


class BillingAutoBillTest(TestCase):
    """Test that auto-billing creates correct invoices."""

    def setUp(self):
        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.user = User.objects.create_user(
            username="test1", email="test@test.com", first_name="Test", last_name="User",
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
            status="WAITING_TRIAGE",
        )

    def test_get_or_create_visit_invoice(self):
        invoice = billing_services.get_or_create_visit_invoice(self.visit, self.user)
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.patient, self.patient)
        self.assertEqual(invoice.visit, self.visit)
        self.assertEqual(invoice.status, Invoice.Status.PENDING)
        # Second call should return same invoice
        invoice2 = billing_services.get_or_create_visit_invoice(self.visit, self.user)
        self.assertEqual(invoice.pk, invoice2.pk)

    def test_add_invoice_item(self):
        invoice = billing_services.get_or_create_visit_invoice(self.visit, self.user)
        billing_services.add_invoice_item(invoice, "Test Item", quantity=2, unit_price=Decimal("5000"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.total_amount, Decimal("10000"))
        self.assertEqual(invoice.items.count(), 1)

    def test_add_multiple_items(self):
        invoice = billing_services.get_or_create_visit_invoice(self.visit, self.user)
        billing_services.add_invoice_item(invoice, "Item 1", quantity=1, unit_price=Decimal("5000"))
        billing_services.add_invoice_item(invoice, "Item 2", quantity=3, unit_price=Decimal("2000"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.total_amount, Decimal("11000"))
        self.assertEqual(invoice.items.count(), 2)

    def test_generate_invoice_number(self):
        num = billing_services.generate_invoice_number()
        self.assertTrue(num.startswith("INV-2026-"))


class PaymentModelTest(TestCase):
    """Test Payment model."""

    def setUp(self):
        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.user = User.objects.create_user(
            username="cashier1", email="cash@test.com", first_name="Cash", last_name="ier",
            password="testpass", role="Cashier",
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
            patient=self.patient, visit_number="VIS-2026-000001", status="WAITING_TRIAGE",
        )
        self.invoice = billing_services.get_or_create_visit_invoice(self.visit, self.user)
        billing_services.add_invoice_item(self.invoice, "Test Service", quantity=1, unit_price=Decimal("10000"))

    def test_payment_str(self):
        payment = Payment.objects.create(
            invoice=self.invoice, amount=Decimal("5000"), payment_method="CASH",
            receipt_number="RCP-2026-000001", received_by=self.user,
        )
        self.assertIn("5,000", str(payment))
        self.assertIn("RCP-2026-000001", str(payment))

    def test_generate_receipt_number(self):
        num = cashier_services.generate_receipt_number()
        self.assertTrue(num.startswith("RCP-2026-"))


class CashierServicesTest(TestCase):
    """Test cashier service layer."""

    def setUp(self):
        self.category = PatientCategory.objects.create(name="General", discount_percentage=Decimal("0"))
        self.user = User.objects.create_user(
            username="cashier2", email="cash@test.com", first_name="Cash", last_name="ier",
            password="testpass", role="Cashier",
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
            patient=self.patient, visit_number="VIS-2026-000001", status="WAITING_TRIAGE",
        )
        self.invoice = billing_services.get_or_create_visit_invoice(self.visit, self.user)
        billing_services.add_invoice_item(self.invoice, "Test Service", quantity=1, unit_price=Decimal("10000"))

    def test_process_payment_full(self):
        payment = cashier_services.process_payment(
            self.invoice.pk, Decimal("10000"), "CASH", user=self.user,
        )
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, Decimal("10000"))
        self.assertEqual(payment.payment_method, "CASH")
        self.assertTrue(payment.receipt_number.startswith("RCP-"))
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)
        self.assertEqual(self.invoice.amount_paid, Decimal("10000"))
        self.assertEqual(self.invoice.balance, Decimal("0"))

    def test_process_payment_partial(self):
        payment = cashier_services.process_payment(
            self.invoice.pk, Decimal("3000"), "MPESA", user=self.user,
        )
        self.assertEqual(payment.amount, Decimal("3000"))
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PARTIALLY_PAID)
        self.assertEqual(self.invoice.amount_paid, Decimal("3000"))
        self.assertEqual(self.invoice.balance, Decimal("7000"))

    def test_process_multiple_payments(self):
        cashier_services.process_payment(self.invoice.pk, Decimal("4000"), "CASH", user=self.user)
        cashier_services.process_payment(self.invoice.pk, Decimal("6000"), "CARD", user=self.user)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)
        self.assertEqual(self.invoice.amount_paid, Decimal("10000"))
        self.assertEqual(self.invoice.payments.count(), 2)

    def test_payment_exceeds_balance_raises(self):
        with self.assertRaises(ValueError):
            cashier_services.process_payment(
                self.invoice.pk, Decimal("15000"), "CASH", user=self.user,
            )

    def test_payment_zero_raises(self):
        with self.assertRaises(ValueError):
            cashier_services.process_payment(
                self.invoice.pk, Decimal("0"), "CASH", user=self.user,
            )

    def test_payment_on_paid_invoice_raises(self):
        cashier_services.process_payment(self.invoice.pk, Decimal("10000"), "CASH", user=self.user)
        with self.assertRaises(ValueError):
            cashier_services.process_payment(
                self.invoice.pk, Decimal("1000"), "CASH", user=self.user,
            )

    def test_get_pending_invoices(self):
        pending = cashier_services.get_pending_invoices()
        self.assertEqual(pending.count(), 1)
        cashier_services.process_payment(self.invoice.pk, Decimal("10000"), "CASH", user=self.user)
        pending = cashier_services.get_pending_invoices()
        self.assertEqual(pending.count(), 0)

    def test_get_invoice_payments(self):
        cashier_services.process_payment(self.invoice.pk, Decimal("5000"), "CASH", user=self.user)
        payments = cashier_services.get_invoice_payments(self.invoice.pk)
        self.assertEqual(payments.count(), 1)

    def test_get_all_payments(self):
        cashier_services.process_payment(self.invoice.pk, Decimal("5000"), "CASH", user=self.user)
        all_payments = cashier_services.get_all_payments()
        self.assertEqual(all_payments.count(), 1)

    def test_outstanding_summary(self):
        cashier_services.process_payment(self.invoice.pk, Decimal("3000"), "CASH", user=self.user)
        summary = cashier_services.get_outstanding_summary()
        self.assertEqual(summary["count"], 1)


class CashierViewsTest(TestCase):
    """Test cashier views via Django test client."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="cashier3", email="cash@test.com", first_name="Cash", last_name="ier",
            password="testpass", role="Cashier",
        )
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
            patient=self.patient, visit_number="VIS-2026-000001", status="WAITING_TRIAGE",
        )
        self.invoice = billing_services.get_or_create_visit_invoice(self.visit, self.user)
        billing_services.add_invoice_item(self.invoice, "Test Service", quantity=1, unit_price=Decimal("10000"))
        self.client.login(username="cashier3", password="testpass")

    def test_dashboard_view(self):
        resp = self.client.get("/cashier/")
        self.assertEqual(resp.status_code, 200)

    def test_billing_list_view(self):
        resp = self.client.get("/cashier/billing/")
        self.assertEqual(resp.status_code, 200)

    def test_billing_detail_view(self):
        resp = self.client.get(f"/cashier/billing/{self.invoice.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_pay_view_get(self):
        resp = self.client.get(f"/cashier/invoice/{self.invoice.pk}/pay/")
        self.assertEqual(resp.status_code, 200)

    def test_pay_view_post(self):
        resp = self.client.post(f"/cashier/invoice/{self.invoice.pk}/pay/", {
            "amount": "10000",
            "payment_method": "CASH",
        })
        self.assertEqual(resp.status_code, 302)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)

    def test_receipt_view(self):
        payment = cashier_services.process_payment(
            self.invoice.pk, Decimal("10000"), "CASH", user=self.user,
        )
        resp = self.client.get(f"/cashier/receipt/{payment.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_payment_history_view(self):
        resp = self.client.get("/cashier/history/")
        self.assertEqual(resp.status_code, 200)

    def test_outstanding_view(self):
        resp = self.client.get("/cashier/outstanding/")
        self.assertEqual(resp.status_code, 200)

    def test_partial_payment(self):
        resp = self.client.post(f"/cashier/invoice/{self.invoice.pk}/pay/", {
            "amount": "5000",
            "payment_method": "MPESA",
            "reference_number": "MPESA-12345",
        })
        self.assertEqual(resp.status_code, 302)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PARTIALLY_PAID)
        self.assertEqual(self.invoice.amount_paid, Decimal("5000"))

    def test_payment_exceeds_balance(self):
        resp = self.client.post(f"/cashier/invoice/{self.invoice.pk}/pay/", {
            "amount": "15000",
            "payment_method": "CASH",
        })
        self.assertEqual(resp.status_code, 200)  # re-renders form with error
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PENDING)
