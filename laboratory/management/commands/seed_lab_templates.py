from django.core.management.base import BaseCommand
from laboratory.models import LabTest, LabTestTemplate, LabTestParameter


FBC_PARAMETERS = [
    {"name": "WBC", "unit": "x10\u2079/L", "normal_range": "4.0 - 10.0", "normal_min": 4.0, "normal_max": 10.0},
    {"name": "LYMPH%", "unit": "%", "normal_range": "20 - 40", "normal_min": 20, "normal_max": 40},
    {"name": "LYMPH#", "unit": "x10\u2079/L", "normal_range": "0.6 - 4.1", "normal_min": 0.6, "normal_max": 4.1},
    {"name": "GRAN#", "unit": "x10\u2079/L", "normal_range": "2.0 - 7.8", "normal_min": 2.0, "normal_max": 7.8},
    {"name": "GRAN%", "unit": "%", "normal_range": "50 - 70", "normal_min": 50, "normal_max": 70},
    {"name": "HB", "unit": "g/dL", "normal_range": "11.5 - 18.0", "normal_min": 11.5, "normal_max": 18.0},
    {"name": "RBC", "unit": "x10\u00B9\u00B2/L", "normal_range": "3.5 - 5.5", "normal_min": 3.5, "normal_max": 5.5},
    {"name": "HCT", "unit": "%", "normal_range": "37 - 54", "normal_min": 37, "normal_max": 54},
    {"name": "MCV", "unit": "fL", "normal_range": "80 - 100", "normal_min": 80, "normal_max": 100},
    {"name": "MCH", "unit": "pg", "normal_range": "27 - 34", "normal_min": 27, "normal_max": 34},
    {"name": "MCHC", "unit": "g/dL", "normal_range": "34.7 - 36", "normal_min": 34.7, "normal_max": 36},
    {"name": "RDW-CV", "unit": "%", "normal_range": "11 - 16", "normal_min": 11, "normal_max": 16},
    {"name": "RDW-SD", "unit": "fL", "normal_range": "35 - 56", "normal_min": 35, "normal_max": 56},
    {"name": "PLT", "unit": "x10\u2079/L", "normal_range": "150 - 450", "normal_min": 150, "normal_max": 450},
    {"name": "PCT", "unit": "mL/L", "normal_range": "1.08 - 2.82", "normal_min": 1.08, "normal_max": 2.82},
    {"name": "MPV", "unit": "fL", "normal_range": "6.5 - 12", "normal_min": 6.5, "normal_max": 12},
    {"name": "PDW", "unit": "%", "normal_range": "0 - 17", "normal_min": 0, "normal_max": 17},
    {"name": "MID#", "unit": "x10\u2079/L", "normal_range": "0.1 - 1.5", "normal_min": 0.1, "normal_max": 1.5},
]


class Command(BaseCommand):
    help = "Seed lab test templates with predefined parameters"

    def handle(self, *args, **options):
        self._seed_fbc()
        self.stdout.write(self.style.SUCCESS("Lab test templates seeded."))

    def _seed_fbc(self):
        names_to_try = [
            "FULL HAEMOGRAM (FBC)",
            "FULL HAEMOGRAM",
            "Full Blood Count (FBC)",
            "Full Blood Count",
            "FULL BLOOD COUNT (FBC)",
            "FULL BLOOD COUNT",
            "FBC",
        ]
        lab_test = None
        for name in names_to_try:
            lab_test = LabTest.objects.filter(name__iexact=name).first()
            if lab_test:
                break

        if not lab_test:
            self.stdout.write(self.style.WARNING(
                "Could not find a Full Haemogram/FBC lab test. Skipping FBC template."
            ))
            return

        template, created = LabTestTemplate.objects.get_or_create(
            lab_test=lab_test,
            defaults={"instructions": "Enter result values only. Auto-flagging enabled.", "is_active": True},
        )

        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} template for: {lab_test.name}")

        if created:
            for i, param in enumerate(FBC_PARAMETERS):
                LabTestParameter.objects.create(
                    template=template,
                    name=param["name"],
                    unit=param["unit"],
                    normal_range=param["normal_range"],
                    normal_min=param["normal_min"],
                    normal_max=param["normal_max"],
                    display_order=i,
                )
            self.stdout.write(f"  Added {len(FBC_PARAMETERS)} parameters.")
        else:
            self.stdout.write("  Template already has parameters, skipping.")
