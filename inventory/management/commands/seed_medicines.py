from django.core.management.base import BaseCommand

from inventory.models import MedicineCategory, Medicine, Supplier


class Command(BaseCommand):
    help = "Seed inventory with sample categories, suppliers, and medicines"

    def handle(self, *args, **options):
        categories_data = [
            ("Antibiotics", "Medicines used to treat bacterial infections"),
            ("Analgesics", "Pain relievers"),
            ("Antihypertensives", "Blood pressure medications"),
            ("Antidiabetics", "Diabetes medications"),
            ("Antimalarials", "Medicines for treating malaria"),
            ("Gastrointestinal", "Medicines for digestive system disorders"),
            ("Respiratory", "Medicines for respiratory conditions"),
            ("Vitamins & Supplements", "Nutritional supplements"),
            ("Dermatological", "Skin care medications"),
            ("Ophthalmic", "Eye care medications"),
        ]

        categories = {}
        for name, desc in categories_data:
            cat, _ = MedicineCategory.objects.get_or_create(
                name=name, defaults={"description": desc}
            )
            categories[name] = cat
        self.stdout.write(self.style.SUCCESS(f"Created {len(categories)} categories"))

        suppliers_data = [
            ("MedSupply Nigeria Ltd", "Chidi Okonkwo", "08012345678", "chidi@medsupply.ng", "21 Market Road, Lagos"),
            ("PharmaDist West Africa", "Amina Bello", "08098765432", "amina@pharmadist.ng", "15 Industrial Ave, Abuja"),
            ("HealthLine Distributors", "Emeka Nwosu", "08055512345", "emeka@healthline.ng", "8 Pharmacy Lane, Port Harcourt"),
            ("Global Pharma Imports", "Fatima Abubakar", "08077788899", "fatima@globalpharma.ng", "45 Import Drive, Kano"),
        ]

        suppliers = {}
        for name, contact, phone, email, address in suppliers_data:
            sup, _ = Supplier.objects.get_or_create(
                name=name,
                defaults={
                    "contact_person": contact,
                    "phone": phone,
                    "email": email,
                    "address": address,
                },
            )
            suppliers[name] = sup
        self.stdout.write(self.style.SUCCESS(f"Created {len(suppliers)} suppliers"))

        medicines_data = [
            ("Amoxicillin 500mg", "Amoxicillin", "Antibiotics", "CAPSULE", "500mg", "Capsule", 1500, 800, 50, 30),
            ("Metronidazole 400mg", "Metronidazole", "Antibiotics", "TABLET", "400mg", "Tablet", 800, 400, 50, 30),
            ("Ciprofloxacin 500mg", "Ciprofloxacin", "Antibiotics", "TABLET", "500mg", "Tablet", 2000, 1200, 40, 20),
            ("Paracetamol 500mg", "Paracetamol", "Analgesics", "TABLET", "500mg", "Tablet", 300, 100, 100, 50),
            ("Ibuprofen 400mg", "Ibuprofen", "Analgesics", "TABLET", "400mg", "Tablet", 500, 250, 80, 40),
            ("Tramadol 50mg", "Tramadol", "Analgesics", "TABLET", "50mg", "Tablet", 1500, 800, 30, 15),
            ("Amlodipine 5mg", "Amlodipine", "Antihypertensives", "TABLET", "5mg", "Tablet", 1200, 600, 50, 25),
            ("Losartan 50mg", "Losartan", "Antihypertensives", "TABLET", "50mg", "Tablet", 2500, 1500, 40, 20),
            ("Enalapril 10mg", "Enalapril", "Antihypertensives", "TABLET", "10mg", "Tablet", 1800, 900, 40, 20),
            ("Metformin 500mg", "Metformin", "Antidiabetics", "TABLET", "500mg", "Tablet", 1000, 500, 60, 30),
            ("Glibenclamide 5mg", "Glibenclamide", "Antidiabetics", "TABLET", "5mg", "Tablet", 800, 400, 40, 20),
            ("Artemether/Lumefantrine", "AL Combination", "Antimalarials", "TABLET", "20/120mg", "Tablet", 2500, 1500, 50, 25),
            ("Artesunate 60mg Injection", "Artesunate", "Antimalarials", "INJECTION", "60mg", "Ampoule", 5000, 3000, 20, 10),
            ("Omeprazole 20mg", "Omeprazole", "Gastrointestinal", "CAPSULE", "20mg", "Capsule", 1500, 800, 50, 25),
            ("Loperamide 2mg", "Loperamide", "Gastrointestinal", "TABLET", "2mg", "Tablet", 800, 400, 40, 20),
            ("Salbutamol Inhaler", "Salbutamol", "Respiratory", "INHALER", "100mcg", "Inhaler", 3500, 2000, 30, 15),
            ("Montelukast 10mg", "Montelukast", "Respiratory", "TABLET", "10mg", "Tablet", 2000, 1200, 40, 20),
            ("Vitamin C 1000mg", "Ascorbic Acid", "Vitamins & Supplements", "TABLET", "1000mg", "Tablet", 1500, 800, 60, 30),
            ("Iron/Folic Acid", "Iron Supplement", "Vitamins & Supplements", "TABLET", "200mg/0.4mg", "Tablet", 800, 400, 80, 40),
            ("Hydrocortisone Cream 1%", "Hydrocortisone", "Dermatological", "CREAM", "1%", "Tube", 2500, 1500, 30, 15),
            ("Clotrimazole Cream", "Clotrimazole", "Dermatological", "CREAM", "1%", "Tube", 1800, 1000, 30, 15),
            ("Chloramphenicol Eye Drops", "Chloramphenicol", "Ophthalmic", "DROPS", "0.5%", "Bottle", 1200, 600, 40, 20),
            ("Tropicamide Eye Drops", "Tropicamide", "Ophthalmic", "DROPS", "1%", "Bottle", 3000, 1800, 20, 10),
            ("Pentazocine Injection", "Pentazocine", "Analgesics", "INJECTION", "30mg/ml", "Ampoule", 3000, 1800, 25, 12),
            ("Diazepam 5mg", "Diazepam", "Analgesics", "TABLET", "5mg", "Tablet", 1000, 500, 30, 15),
        ]

        count = 0
        for name, generic, cat_name, form, strength, unit, selling, cost, min_stock, reorder in medicines_data:
            _, created = Medicine.objects.get_or_create(
                name=name,
                defaults={
                    "generic_name": generic,
                    "category": categories[cat_name],
                    "dosage_form": form,
                    "strength": strength,
                    "unit": unit,
                    "selling_price": selling,
                    "cost_price": cost,
                    "minimum_stock": min_stock,
                    "reorder_level": reorder,
                },
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Created {count} medicines"))
