"""
Seed the database with common radiology services.
"""
from django.core.management.base import BaseCommand
from radiology.models import RadiologyService


class Command(BaseCommand):
    help = "Seed radiology services"

    def handle(self, *args, **options):
        services = [
            # X-Ray
            ("Chest X-Ray (PA)", "XRAY", "Chest", "Chest radiograph, posteroanterior view", 15000),
            ("Abdominal X-Ray", "XRAY", "Abdomen", "Plain abdominal radiograph", 15000),
            ("Skull X-Ray", "XRAY", "Skull", "Skull radiograph", 15000),
            ("Spine X-Ray (Lumbar)", "XRAY", "Lumbar Spine", "Lumbar spine radiograph", 20000),
            ("Pelvis X-Ray", "XRAY", "Pelvis", "Pelvis radiograph", 15000),
            ("Chest X-Ray (Lateral)", "XRAY", "Chest", "Lateral chest radiograph", 15000),
            ("Knee X-Ray", "XRAY", "Knee", "Knee joint radiograph", 15000),
            ("Hand X-Ray", "XRAY", "Hand", "Hand/wrist radiograph", 12000),
            ("Foot X-Ray", "XRAY", "Foot", "Foot/ankle radiograph", 12000),

            # Ultrasound
            ("Abdominal Ultrasound", "ULTRASOUND", "Abdomen", "Ultrasound of abdomen and pelvis", 25000),
            ("Pelvic Ultrasound", "ULTRASOUND", "Pelvis", "Pelvic ultrasound scan", 25000),
            ("Obstetric Ultrasound", "ULTRASOUND", "Uterus", "Obstetric ultrasound scan", 30000),
            ("Thyroid Ultrasound", "ULTRASOUND", "Thyroid", "Ultrasound of thyroid gland", 25000),
            ("Breast Ultrasound", "ULTRASOUND", "Breast", "Ultrasound of breast", 25000),
            ("Scrotal Ultrasound", "ULTRASOUND", "Scrotum", "Ultrasound of scrotum", 25000),
            ("Renal Ultrasound", "ULTRASOUND", "Kidneys", "Ultrasound of kidneys", 25000),

            # MRI
            ("MRI Brain", "MRI", "Brain", "MRI scan of the brain", 80000),
            ("MRI Spine", "MRI", "Spine", "MRI scan of the spine", 80000),

            # CT Scan
            ("CT Brain", "CT_SCAN", "Brain", "CT scan of the brain", 60000),
            ("CT Abdomen", "CT_SCAN", "Abdomen", "CT scan of the abdomen", 60000),
            ("CT Chest", "CT_SCAN", "Chest", "CT scan of the chest", 60000),
        ]

        created_count = 0
        for name, stype, body_part, desc, price in services:
            _, created = RadiologyService.objects.get_or_create(
                name=name,
                defaults={
                    "service_type": stype,
                    "body_part": body_part,
                    "description": desc,
                    "price": price,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"  + {name}")
            else:
                self.stdout.write(f"  = {name} (exists)")

        self.stdout.write(self.style.SUCCESS(f"\nSeeded {created_count} radiology services (total: {RadiologyService.objects.count()})"))
