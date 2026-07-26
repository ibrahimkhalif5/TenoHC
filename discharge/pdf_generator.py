"""
PDF generation for discharge summaries using ReportLab.
"""
import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Spacer, Paragraph

from core.document_service import DocumentTemplateService, SectionDivider
from core.constants import DOCTOR_NAME


class DischargePDFGenerator(DocumentTemplateService):
    """Generate professional A4 PDF for discharge summaries."""

    def __init__(self, summary, **kwargs):
        super().__init__(**kwargs)
        self.summary = summary
        self.admission = summary.admission
        self.patient = self.admission.patient
        self.ward = self.admission.ward
        self.room = self.admission.room
        self.bed = self.admission.bed

    def get_title(self):
        return "DISCHARGE SUMMARY"

    def build_elements(self):
        els = []
        els.extend(self.build_hospital_header())
        els.extend(self.build_title_block())

        # Section A: Patient Information
        els.extend(self._build_patient_info())

        # Section B: Clinical Information
        els.extend(self._build_clinical_info())

        # Section C: Medications
        els.extend(self._build_medications())

        # Section D: Follow-up Instructions
        els.extend(self._build_followup())

        # Section E: Doctor Information
        els.extend(self._build_doctor_info())

        return els

    def _build_patient_info(self):
        s = self.styles
        admission = self.admission
        patient = self.patient
        ward = self.ward
        room = self.room
        bed = self.bed
        summary = self.summary
        half = self.content_width / 2

        els = []
        els.extend(self.build_section_heading("PATIENT INFORMATION"))

        rows = [
            self.build_kv_row("Patient Number", patient.patient_number),
            self.build_kv_row("Patient Name", patient.full_name),
            self.build_kv_row("Age", f"{patient.age} years"),
            self.build_kv_row("Gender", patient.get_gender_display()),
            self.build_kv_row("Phone Number", patient.phone),
            self.build_kv_row("National ID", patient.national_id or "—"),
            self.build_kv_row("Admission Number", f"ADM-{admission.pk:06d}"),
            self.build_kv_row("Admission Date", admission.admission_date.strftime("%d %b %Y")),
            self.build_kv_row(
                "Discharge Date",
                admission.discharge_date.strftime("%d %b %Y") if admission.discharge_date else "—",
            ),
            self.build_kv_row("Length of Stay", f"{summary.length_of_stay} day(s)"),
            self.build_kv_row("Ward", ward.name),
            self.build_kv_row("Room", f"{room.room_number} ({room.get_room_type_display()})"),
            self.build_kv_row("Bed Number", bed.bed_number),
            self.build_kv_row(
                "Attending Doctor",
                DOCTOR_NAME,
            ),
        ]

        pat_table = self.build_kv_table(rows, [half, half])
        els.append(pat_table)
        els.append(self._divider())
        return els

    def _build_clinical_info(self):
        summary = self.summary
        els = []
        blocks = []
        blocks.extend(self.build_text_block("Primary Diagnosis", summary.primary_diagnosis))
        blocks.extend(self.build_text_block("Secondary Diagnosis", summary.secondary_diagnosis))
        blocks.extend(self.build_text_block("Reason for Admission", summary.reason_for_admission))
        blocks.extend(self.build_text_block("History of Present Illness", summary.history_of_present_illness))
        blocks.extend(self.build_text_block("Clinical Findings", summary.clinical_findings))
        blocks.extend(self.build_text_block("Investigations Performed", summary.investigations_performed))
        blocks.extend(self.build_text_block("Procedures Done During Admission", summary.procedures_done))
        blocks.extend(self.build_text_block("Treatment Given", summary.treatment_given))
        blocks.extend(self.build_text_block("Patient Progress During Admission", summary.patient_progress))
        blocks.extend(self.build_text_block("Condition on Discharge", summary.condition_on_discharge))
        els.extend(self.build_section_heading("CLINICAL INFORMATION"))
        els.extend(blocks)
        els.append(Spacer(1, 4))
        return els

    def _build_medications(self):
        meds = list(self.summary.discharge_medications.all())
        els = []
        els.extend(self.build_section_heading("MEDICATION ON DISCHARGE"))
        if meds:
            headers = ["Medicine", "Dosage", "Frequency", "Duration", "Instructions"]
            rows = []
            for med in meds:
                rows.append([
                    med.medicine_name,
                    med.dosage or "—",
                    med.frequency or "—",
                    med.duration or "—",
                    med.instructions or "—",
                ])
            widths = [self.content_width * w for w in (0.25, 0.15, 0.2, 0.15, 0.25)]
            els.append(self.build_data_table(headers, rows, widths))
        else:
            els.append(Paragraph("No discharge medications recorded.", self.styles["FieldValue"]))
        els.append(Spacer(1, 4))
        return els

    def _build_followup(self):
        summary = self.summary
        els = []
        blocks = []
        blocks.extend(self.build_text_block("Doctor Advice", summary.doctor_advice))
        blocks.extend(self.build_text_block(
            "Follow-up Date",
            summary.follow_up_date.strftime("%d %b %Y") if summary.follow_up_date else "Not specified",
        ))
        blocks.extend(self.build_text_block("Lifestyle Advice", summary.lifestyle_advice))
        blocks.extend(self.build_text_block("Diet Advice", summary.diet_advice))
        blocks.extend(self.build_text_block("Activity Restrictions", summary.activity_restrictions))
        blocks.extend(self.build_text_block("Warning Signs", summary.warning_signs))
        els.extend(self.build_section_heading("FOLLOW-UP INSTRUCTIONS"))
        els.extend(blocks)
        els.append(Spacer(1, 4))
        return els

    def _build_doctor_info(self):
        import os
        from reportlab.platypus import Image as RLImage
        summary = self.summary
        admission = self.admission
        s = self.styles
        half = self.content_width / 2

        doctor_name = DOCTOR_NAME

        els = []
        els.extend(self.build_section_heading("DOCTOR INFORMATION"))

        rows = [
            self.build_kv_row("Doctor Name", doctor_name),
            self.build_kv_row(
                "Date",
                summary.finalized_at.strftime("%d %b %Y") if summary.finalized_at else date.today().strftime("%d %b %Y"),
            ),
        ]
        doc_table = self.build_kv_table(rows, [half, half])
        els.append(doc_table)

        if summary.doctor_signature and os.path.exists(summary.doctor_signature.path):
            try:
                sig_img = RLImage(summary.doctor_signature.path, width=80, height=40)
                els.append(Spacer(1, 4))
                els.append(Paragraph("<b>Doctor Signature:</b>", s["FieldLabel"]))
                els.append(sig_img)
            except Exception:
                pass

        els.append(Spacer(1, 4))
        return els

    def _divider(self):
        return SectionDivider(self.content_width)


def generate_discharge_pdf(summary):
    """Generate a professional A4 PDF for the discharge summary."""
    gen = DischargePDFGenerator(summary)
    return gen.generate()
