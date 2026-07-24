from django.core.management.base import BaseCommand
from laboratory.models import LabTest


SEED_DATA = [
    # Haematology
    {"name": "Full Blood Count (FBC)", "category": "HAEMATOLOGY", "price": 3500, "normal_range": "WBC: 4.5-11.0 x10^9/L", "unit": "x10^9/L", "turnaround_time": "24 hours"},
    {"name": "Haemoglobin", "category": "HAEMATOLOGY", "price": 2000, "normal_range": "12.0-16.0 g/dL", "unit": "g/dL", "turnaround_time": "24 hours"},
    {"name": "Erythrocyte Sedimentation Rate (ESR)", "category": "HAEMATOLOGY", "price": 1500, "normal_range": "0-20 mm/hr", "unit": "mm/hr", "turnaround_time": "24 hours"},
    {"name": "Platelet Count", "category": "HAEMATOLOGY", "price": 2500, "normal_range": "150-400 x10^9/L", "unit": "x10^9/L", "turnaround_time": "24 hours"},
    # Chemistry
    {"name": "Blood Sugar (Fasting)", "category": "CHEMISTRY", "price": 2000, "normal_range": "70-100 mg/dL", "unit": "mg/dL", "turnaround_time": "2 hours"},
    {"name": "Blood Sugar (Random)", "category": "CHEMISTRY", "price": 2000, "normal_range": "70-140 mg/dL", "unit": "mg/dL", "turnaround_time": "2 hours"},
    {"name": "Liver Function Test (LFT)", "category": "CHEMISTRY", "price": 5000, "normal_range": "ALT: 7-56 U/L", "unit": "U/L", "turnaround_time": "24 hours"},
    {"name": "Kidney Function Test (KFT)", "category": "CHEMISTRY", "price": 5000, "normal_range": "Creatinine: 0.6-1.2 mg/dL", "unit": "mg/dL", "turnaround_time": "24 hours"},
    {"name": "Lipid Profile", "category": "CHEMISTRY", "price": 4500, "normal_range": "Total Cholesterol: <200 mg/dL", "unit": "mg/dL", "turnaround_time": "24 hours"},
    {"name": "Electrolytes", "category": "CHEMISTRY", "price": 4000, "normal_range": "Na: 135-145 mEq/L", "unit": "mEq/L", "turnaround_time": "4 hours"},
    {"name": "Uric Acid", "category": "CHEMISTRY", "price": 3000, "normal_range": "3.5-7.0 mg/dL", "unit": "mg/dL", "turnaround_time": "24 hours"},
    # Microbiology
    {"name": "Malaria Parasite (MP)", "category": "MICROBIOLOGY", "price": 2000, "normal_range": "Negative", "unit": "", "turnaround_time": "2 hours"},
    {"name": "Urinalysis (UA)", "category": "MICROBIOLOGY", "price": 1500, "normal_range": "Clear, yellow, pH 4.5-8.0", "unit": "", "turnaround_time": "2 hours"},
    {"name": "Urine Culture & Sensitivity", "category": "MICROBIOLOGY", "price": 5000, "normal_range": "No growth", "unit": "", "turnaround_time": "48 hours"},
    {"name": "Stool Analysis", "category": "MICROBIOLOGY", "price": 2000, "normal_range": "No ova or parasites", "unit": "", "turnaround_time": "4 hours"},
    {"name": "Blood Culture & Sensitivity", "category": "MICROBIOLOGY", "price": 6000, "normal_range": "No growth", "unit": "", "turnaround_time": "48 hours"},
    # Immunology
    {"name": "HIV Test", "category": "IMMUNOLOGY", "price": 3000, "normal_range": "Non-reactive", "unit": "", "turnaround_time": "2 hours"},
    {"name": "Hepatitis B Surface Antigen (HBsAg)", "category": "IMMUNOLOGY", "price": 3500, "normal_range": "Non-reactive", "unit": "", "turnaround_time": "4 hours"},
    {"name": "Pregnancy Test (hCG)", "category": "IMMUNOLOGY", "price": 2000, "normal_range": "Negative", "unit": "", "turnaround_time": "30 minutes"},
    # Pathology
    {"name": "Blood Group & Rhesus", "category": "PATHOLOGY", "price": 2500, "normal_range": "N/A", "unit": "", "turnaround_time": "2 hours"},
    {"name": "Prothrombin Time (PT)", "category": "PATHOLOGY", "price": 3500, "normal_range": "11-13.5 seconds", "unit": "seconds", "turnaround_time": "4 hours"},
]


class Command(BaseCommand):
    help = "Seed laboratory test data"

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for data in SEED_DATA:
            obj, created = LabTest.objects.update_or_create(
                name=data["name"],
                defaults={
                    "category": data["category"],
                    "price": data["price"],
                    "normal_range": data.get("normal_range", ""),
                    "unit": data.get("unit", ""),
                    "turnaround_time": data.get("turnaround_time", ""),
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Lab tests: {created_count} created, {updated_count} updated "
                f"(total: {created_count + updated_count})"
            )
        )
