from datetime import date, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model

from inventory.models import (
    Medicine, MedicineCategory, Purchase, PurchaseItem, Stock,
    StockMovement, Supplier,
)
from inventory.services import (
    adjust_stock, cancel_purchase, create_purchase, dispense_stock,
    get_all_medicines, get_all_stock, get_all_purchases, get_dashboard_stats,
    get_expiring_medicines, get_expired_stock, get_low_stock_medicines,
    get_medicine, get_purchase, get_stock_for_medicine, get_stock_movements,
    mark_expired, receive_purchase,
)

User = get_user_model()


class InventoryModelsTest(TestCase):
    def setUp(self):
        self.category = MedicineCategory.objects.create(
            name="Analgesics", description="Pain relievers"
        )
        self.supplier = Supplier.objects.create(
            name="MedSupply Ltd",
            contact_person="Chidi",
            phone="08012345678",
            email="chidi@medsupply.ng",
            address="21 Market Road, Lagos",
        )
        self.medicine = Medicine.objects.create(
            name="Paracetamol 500mg",
            generic_name="Paracetamol",
            category=self.category,
            dosage_form="TABLET",
            strength="500mg",
            unit="Tablet",
            selling_price=300,
            cost_price=100,
            minimum_stock=50,
            reorder_level=30,
        )

    def test_medicine_str(self):
        self.assertEqual(str(self.medicine), "Paracetamol 500mg (500mg)")

    def test_medicine_current_stock_no_stock(self):
        self.assertEqual(self.medicine.current_stock, 0)

    def test_medicine_low_stock_no_stock(self):
        self.assertTrue(self.medicine.is_low_stock)

    def test_medicine_not_expired_stock_no_stock(self):
        self.assertFalse(self.medicine.is_expired_stock)

    def test_category_str(self):
        self.assertEqual(str(self.category), "Analgesics")

    def test_supplier_str(self):
        self.assertEqual(str(self.supplier), "MedSupply Ltd")

    def test_stock_str(self):
        stock = Stock.objects.create(
            medicine=self.medicine,
            batch_number="BATCH001",
            quantity=100,
            expiry_date=date.today() + timedelta(days=365),
            purchase_price=100,
        )
        self.assertEqual(str(stock), "Paracetamol 500mg - Batch BATCH001 (100 units)")

    def test_stock_is_expired(self):
        stock = Stock.objects.create(
            medicine=self.medicine,
            batch_number="BATCH002",
            quantity=50,
            expiry_date=date.today() - timedelta(days=1),
            purchase_price=100,
        )
        self.assertTrue(stock.is_expired)

    def test_stock_not_expired(self):
        stock = Stock.objects.create(
            medicine=self.medicine,
            batch_number="BATCH003",
            quantity=50,
            expiry_date=date.today() + timedelta(days=30),
            purchase_price=100,
        )
        self.assertFalse(stock.is_expired)

    def test_stock_movement_str(self):
        movement = StockMovement.objects.create(
            medicine=self.medicine,
            movement_type="PURCHASE",
            quantity=100,
            batch_number="BATCH001",
            reference="PUR-001",
        )
        self.assertEqual(str(movement), "Paracetamol 500mg: +100 (Purchase (Stock In))")


class InventoryServicesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",
            role="pharmacist",
        )
        self.category = MedicineCategory.objects.create(name="Analgesics")
        self.supplier = Supplier.objects.create(
            name="MedSupply Ltd",
            contact_person="Chidi",
            phone="08012345678",
            email="chidi@medsupply.ng",
            address="21 Market Road, Lagos",
        )
        self.medicine = Medicine.objects.create(
            name="Paracetamol 500mg",
            generic_name="Paracetamol",
            category=self.category,
            dosage_form="TABLET",
            strength="500mg",
            unit="Tablet",
            selling_price=300,
            cost_price=100,
            minimum_stock=50,
            reorder_level=30,
        )

    def test_get_all_medicines(self):
        medicines = get_all_medicines()
        self.assertIn(self.medicine, medicines)

    def test_get_medicine(self):
        result = get_medicine(self.medicine.pk)
        self.assertEqual(result, self.medicine)

    def test_create_purchase(self):
        purchase = create_purchase(
            supplier_id=self.supplier.pk,
            purchase_date=date.today(),
            invoice_number="INV-001",
            items_data=[
                {
                    "medicine_id": self.medicine.pk,
                    "quantity": 100,
                    "unit_cost": 100,
                    "batch_number": "BATCH001",
                    "expiry_date": date.today() + timedelta(days=365),
                }
            ],
            notes="Test purchase",
            user=self.user,
        )
        self.assertIsNotNone(purchase)
        self.assertEqual(purchase.total_amount, 10000)
        self.assertEqual(purchase.status, "PENDING")
        items = PurchaseItem.objects.filter(purchase=purchase)
        self.assertEqual(items.count(), 1)

    def test_receive_purchase(self):
        purchase = create_purchase(
            supplier_id=self.supplier.pk,
            purchase_date=date.today(),
            invoice_number="INV-002",
            items_data=[
                {
                    "medicine_id": self.medicine.pk,
                    "quantity": 100,
                    "unit_cost": 100,
                    "batch_number": "BATCH001",
                    "expiry_date": date.today() + timedelta(days=365),
                }
            ],
            user=self.user,
        )
        receive_purchase(purchase.pk, self.user)
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "RECEIVED")
        stock = Stock.objects.get(medicine=self.medicine, batch_number="BATCH001")
        self.assertEqual(stock.quantity, 100)
        self.medicine.refresh_from_db()
        self.assertEqual(self.medicine.current_stock, 100)
        self.assertFalse(self.medicine.is_low_stock)
        movements = StockMovement.objects.filter(
            medicine=self.medicine, batch_number="BATCH001"
        )
        self.assertEqual(movements.count(), 1)
        self.assertEqual(movements.first().movement_type, "PURCHASE")

    def test_dispense_stock_fifo(self):
        purchase = create_purchase(
            supplier_id=self.supplier.pk,
            purchase_date=date.today(),
            invoice_number="INV-003",
            items_data=[
                {
                    "medicine_id": self.medicine.pk,
                    "quantity": 100,
                    "unit_cost": 80,
                    "batch_number": "BATCH_OLD",
                    "expiry_date": date.today() + timedelta(days=90),
                },
                {
                    "medicine_id": self.medicine.pk,
                    "quantity": 50,
                    "unit_cost": 100,
                    "batch_number": "BATCH_NEW",
                    "expiry_date": date.today() + timedelta(days=365),
                },
            ],
            user=self.user,
        )
        receive_purchase(purchase.pk, self.user)
        dispense_stock(
            medicine_id=self.medicine.pk,
            quantity=30,
            reference="VIS-001",
            user=self.user,
        )
        old_stock = Stock.objects.get(
            medicine=self.medicine, batch_number="BATCH_OLD"
        )
        self.assertEqual(old_stock.quantity, 70)
        new_stock = Stock.objects.get(
            medicine=self.medicine, batch_number="BATCH_NEW"
        )
        self.assertEqual(new_stock.quantity, 50)
        self.medicine.refresh_from_db()
        self.assertEqual(self.medicine.current_stock, 120)
        movements = StockMovement.objects.filter(
            medicine=self.medicine, movement_type="DISPENSE"
        )
        self.assertEqual(movements.count(), 1)
        self.assertEqual(movements.first().quantity, -30)

    def test_adjust_stock(self):
        purchase = create_purchase(
            supplier_id=self.supplier.pk,
            purchase_date=date.today(),
            invoice_number="INV-004",
            items_data=[
                {
                    "medicine_id": self.medicine.pk,
                    "quantity": 100,
                    "unit_cost": 100,
                    "batch_number": "BATCH001",
                    "expiry_date": date.today() + timedelta(days=365),
                }
            ],
            user=self.user,
        )
        receive_purchase(purchase.pk, self.user)
        adjust_stock(
            medicine_id=self.medicine.pk,
            batch_number="BATCH001",
            new_quantity=90,
            reason="Damaged tablets",
            user=self.user,
        )
        stock = Stock.objects.get(medicine=self.medicine, batch_number="BATCH001")
        self.assertEqual(stock.quantity, 90)
        self.medicine.refresh_from_db()
        self.assertEqual(self.medicine.current_stock, 90)

    def test_cancel_purchase(self):
        purchase = create_purchase(
            supplier_id=self.supplier.pk,
            purchase_date=date.today(),
            invoice_number="INV-005",
            items_data=[
                {
                    "medicine_id": self.medicine.pk,
                    "quantity": 100,
                    "unit_cost": 100,
                    "batch_number": "BATCH001",
                    "expiry_date": date.today() + timedelta(days=365),
                }
            ],
            user=self.user,
        )
        cancel_purchase(purchase.pk)
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "CANCELLED")

    def test_get_low_stock_medicines(self):
        purchase = create_purchase(
            supplier_id=self.supplier.pk,
            purchase_date=date.today(),
            invoice_number="INV-006",
            items_data=[
                {
                    "medicine_id": self.medicine.pk,
                    "quantity": 20,
                    "unit_cost": 100,
                    "batch_number": "BATCH001",
                    "expiry_date": date.today() + timedelta(days=365),
                }
            ],
            user=self.user,
        )
        receive_purchase(purchase.pk, self.user)
        low_stock = get_low_stock_medicines()
        self.assertIn(self.medicine, low_stock)

    def test_get_expiring_medicines(self):
        purchase = create_purchase(
            supplier_id=self.supplier.pk,
            purchase_date=date.today(),
            invoice_number="INV-007",
            items_data=[
                {
                    "medicine_id": self.medicine.pk,
                    "quantity": 100,
                    "unit_cost": 100,
                    "batch_number": "BATCH001",
                    "expiry_date": date.today() + timedelta(days=15),
                }
            ],
            user=self.user,
        )
        receive_purchase(purchase.pk, self.user)
        expiring = get_expiring_medicines(days=30)
        stock = Stock.objects.get(medicine=self.medicine, batch_number="BATCH001")
        self.assertIn(stock, list(expiring))

    def test_mark_expired(self):
        purchase = create_purchase(
            supplier_id=self.supplier.pk,
            purchase_date=date.today(),
            invoice_number="INV-008",
            items_data=[
                {
                    "medicine_id": self.medicine.pk,
                    "quantity": 100,
                    "unit_cost": 100,
                    "batch_number": "BATCH001",
                    "expiry_date": date.today() - timedelta(days=1),
                }
            ],
            user=self.user,
        )
        receive_purchase(purchase.pk, self.user)
        mark_expired(
            medicine_id=self.medicine.pk,
            batch_number="BATCH001",
            user=self.user,
        )
        movements = StockMovement.objects.filter(
            medicine=self.medicine, movement_type="EXPIRED"
        )
        self.assertEqual(movements.count(), 1)
        stock = Stock.objects.get(medicine=self.medicine, batch_number="BATCH001")
        self.assertEqual(stock.quantity, 0)

    def test_get_dashboard_stats(self):
        stats = get_dashboard_stats()
        self.assertIn("total_medicines", stats)
        self.assertIn("total_stock_value", stats)
        self.assertIn("low_stock_count", stats)
        self.assertIn("expiring_count", stats)
        self.assertEqual(stats["total_medicines"], 1)


class InventoryViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",
            role="pharmacist",
        )
        self.client.login(username="testuser", password="testpass123")
        self.category = MedicineCategory.objects.create(name="Analgesics")
        self.supplier = Supplier.objects.create(
            name="MedSupply Ltd",
            contact_person="Chidi",
            phone="08012345678",
            email="chidi@medsupply.ng",
            address="21 Market Road, Lagos",
        )
        self.medicine = Medicine.objects.create(
            name="Paracetamol 500mg",
            generic_name="Paracetamol",
            category=self.category,
            dosage_form="TABLET",
            strength="500mg",
            unit="Tablet",
            selling_price=300,
            cost_price=100,
            minimum_stock=50,
            reorder_level=30,
        )

    def test_dashboard_view(self):
        response = self.client.get("/inventory/")
        self.assertEqual(response.status_code, 200)

    def test_medicine_list_view(self):
        response = self.client.get("/inventory/medicines/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paracetamol 500mg")

    def test_medicine_detail_view(self):
        response = self.client.get(f"/inventory/medicines/{self.medicine.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paracetamol 500mg")

    def test_medicine_create_view_get(self):
        response = self.client.get("/inventory/medicines/create/")
        self.assertEqual(response.status_code, 200)

    def test_medicine_create_view_post(self):
        response = self.client.post(
            "/inventory/medicines/create/",
            {
                "name": "Ibuprofen 200mg",
                "generic_name": "Ibuprofen",
                "category": self.category.pk,
                "dosage_form": "TABLET",
                "strength": "200mg",
                "unit": "Tablet",
                "selling_price": 500,
                "cost_price": 250,
                "minimum_stock": 40,
                "reorder_level": 20,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Medicine.objects.filter(name="Ibuprofen 200mg").exists())

    def test_supplier_list_view(self):
        response = self.client.get("/inventory/suppliers/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "MedSupply Ltd")

    def test_supplier_create_view_post(self):
        response = self.client.post(
            "/inventory/suppliers/create/",
            {
                "name": "New Supplier",
                "contact_person": "Test",
                "phone": "08011112222",
                "email": "test@supplier.ng",
                "address": "123 Test Street",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Supplier.objects.filter(name="New Supplier").exists())

    def test_purchase_list_view(self):
        response = self.client.get("/inventory/purchases/")
        self.assertEqual(response.status_code, 200)

    def test_purchase_create_view_get(self):
        response = self.client.get("/inventory/purchases/create/")
        self.assertEqual(response.status_code, 200)

    def test_stock_list_view(self):
        response = self.client.get("/inventory/stock/")
        self.assertEqual(response.status_code, 200)

    def test_low_stock_view(self):
        response = self.client.get("/inventory/low-stock/")
        self.assertEqual(response.status_code, 200)

    def test_expiring_view(self):
        response = self.client.get("/inventory/expiring/")
        self.assertEqual(response.status_code, 200)

    def test_movements_view(self):
        response = self.client.get("/inventory/movements/")
        self.assertEqual(response.status_code, 200)

    def test_medicine_search_api(self):
        response = self.client.get(
            "/inventory/api/medicines/?q=paracetamol"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data) > 0)
