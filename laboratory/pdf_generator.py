"""
Modern PDF generation for Laboratory Reports.
"""
import os

from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    Spacer, Paragraph, Table, TableStyle, HRFlowable, Image,
)

from core.document_service import DocumentTemplateService, PAGE_WIDTH


# ── Color palette ──────────────────────────────────────────────────
PRIMARY = colors.HexColor("#0d6efd")
DARK = colors.HexColor("#1a1d21")
GRAY = colors.HexColor("#6c757d")
LIGHT_GRAY = colors.HexColor("#f8f9fa")
BORDER = colors.HexColor("#dee2e6")
SUCCESS = colors.HexColor("#198754")
DANGER = colors.HexColor("#dc3545")
WARNING = colors.HexColor("#ffc107")
INFO_BG = colors.HexColor("#cff4fc")
DANGER_BG = colors.HexColor("#f8d7da")
SUCCESS_BG = colors.HexColor("#d1e7dd")


class LabReportPDFGenerator(DocumentTemplateService):
    """Generate a modern A4 PDF lab report."""

    def __init__(self, visit_id, **kwargs):
        super().__init__(**kwargs)
        from triage.models import Visit
        from laboratory.models import LabRequest

        self.visit = (
            Visit.objects
            .select_related("patient", "patient__patient_category")
            .prefetch_related("triage_assessments")
            .get(pk=visit_id)
        )
        self.patient = self.visit.patient
        self.lab_requests = (
            LabRequest.objects
            .filter(visit_id=visit_id)
            .select_related("lab_test", "completed_by", "requested_by")
            .prefetch_related("result_values__parameter")
            .order_by("created_at")
        )

    def get_title(self):
        return "LABORATORY REPORT"

    def _build_styles(self):
        s = super()._build_styles()

        s.add(ParagraphStyle(
            name="CenteredHospitalName",
            parent=s["Normal"],
            fontSize=18, leading=22, alignment=TA_CENTER,
            spaceAfter=2, spaceBefore=4,
            textColor=DARK,
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="CenteredHospitalInfo",
            parent=s["Normal"],
            fontSize=8, leading=11, alignment=TA_CENTER,
            textColor=GRAY,
        ))
        s.add(ParagraphStyle(
            name="ReportTitle",
            parent=s["Normal"],
            fontSize=14, leading=18, alignment=TA_CENTER,
            spaceBefore=8, spaceAfter=4,
            textColor=PRIMARY,
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="SectionTitle",
            parent=s["Normal"],
            fontSize=10, leading=13,
            spaceBefore=12, spaceAfter=4,
            textColor=PRIMARY,
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="PatientLabel",
            parent=s["Normal"],
            fontSize=8, leading=10,
            textColor=GRAY,
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="PatientValue",
            parent=s["Normal"],
            fontSize=9, leading=12,
            textColor=DARK,
            fontName="Helvetica",
        ))
        s.add(ParagraphStyle(
            name="TestName",
            parent=s["Normal"],
            fontSize=11, leading=14,
            spaceBefore=10, spaceAfter=4,
            textColor=DARK,
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="TableCellModern",
            parent=s["Normal"],
            fontSize=8, leading=10,
            textColor=DARK,
            fontName="Helvetica",
        ))
        s.add(ParagraphStyle(
            name="TableCellBold",
            parent=s["Normal"],
            fontSize=8, leading=10,
            textColor=DARK,
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="TableHeaderModern",
            parent=s["Normal"],
            fontSize=8, leading=10,
            textColor=colors.white,
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="FlagLow",
            parent=s["Normal"],
            fontSize=8, leading=10,
            textColor=PRIMARY,
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="FlagHigh",
            parent=s["Normal"],
            fontSize=8, leading=10,
            textColor=DANGER,
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="FlagNormal",
            parent=s["Normal"],
            fontSize=8, leading=10,
            textColor=SUCCESS,
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="SmallGray",
            parent=s["Normal"],
            fontSize=7, leading=9,
            textColor=GRAY,
            fontName="Helvetica",
        ))
        s.add(ParagraphStyle(
            name="FooterModern",
            parent=s["Normal"],
            fontSize=7, leading=9, alignment=TA_CENTER,
            textColor=GRAY,
            fontName="Helvetica-Oblique",
        ))

        return s

    def build_elements(self):
        els = []
        els.extend(self._build_centered_header())
        els.extend(self._build_patient_section())
        els.extend(self._build_vitals_section())
        els.extend(self._build_tests_section())
        return els

    # ── Centered hospital header ────────────────────────────────────

    def _build_centered_header(self):
        s = self.styles
        hospital = self.hospital
        els = []

        # Logo centered
        if hospital.logo and os.path.exists(hospital.logo.path):
            try:
                img = Image(hospital.logo.path, width=60, height=60)
                img.hAlign = "CENTER"
                els.append(img)
            except Exception:
                pass

        # Hospital name centered
        els.append(Paragraph(hospital.name, s["CenteredHospitalName"]))

        # Address
        if hospital.address:
            els.append(Paragraph(hospital.address, s["CenteredHospitalInfo"]))

        # Contact line
        parts = []
        if hospital.telephone:
            parts.append(f"Tel: {hospital.telephone}")
        if hospital.email:
            parts.append(f"Email: {hospital.email}")
        if parts:
            els.append(Paragraph("  |  ".join(parts), s["CenteredHospitalInfo"]))

        els.append(Spacer(1, 4))

        # Decorative divider
        els.append(HRFlowable(
            width="100%", thickness=2,
            color=PRIMARY,
            spaceAfter=2,
        ))
        els.append(HRFlowable(
            width="60%", thickness=0.5,
            color=BORDER,
            spaceAfter=4,
        ))

        # Report title
        els.append(Paragraph(self.get_title(), s["ReportTitle"]))

        els.append(HRFlowable(
            width="100%", thickness=0.5,
            color=BORDER,
            spaceAfter=6,
        ))

        return els

    # ── Patient info section ────────────────────────────────────────

    def _build_patient_section(self):
        s = self.styles
        patient = self.patient
        visit = self.visit
        w = self.content_width

        first_req = self.lab_requests.first()
        doctor_name = first_req.requested_by.get_full_name() if first_req and first_req.requested_by else "—"

        tech_name = "—"
        for r in self.lab_requests:
            if r.completed_by:
                tech_name = r.completed_by.get_full_name()
                break

        completed_date = "—"
        for r in self.lab_requests:
            if r.completed_at:
                completed_date = r.completed_at.strftime("%d %b %Y %H:%M")
                break

        requested_date = "—"
        if first_req and first_req.created_at:
            requested_date = first_req.created_at.strftime("%d %b %Y %H:%M")

        # Build a clean 3-column table
        col = w / 3
        data = [
            [
                Paragraph("<b>Patient Name</b>", s["PatientLabel"]),
                Paragraph("<b>Patient Number</b>", s["PatientLabel"]),
                Paragraph("<b>Visit Number</b>", s["PatientLabel"]),
            ],
            [
                Paragraph(patient.full_name, s["PatientValue"]),
                Paragraph(patient.patient_number, s["PatientValue"]),
                Paragraph(visit.visit_number, s["PatientValue"]),
            ],
            [
                Spacer(1, 4),
                Spacer(1, 4),
                Spacer(1, 4),
            ],
            [
                Paragraph("<b>Age / Gender</b>", s["PatientLabel"]),
                Paragraph("<b>Phone</b>", s["PatientLabel"]),
                Paragraph("<b>Payment Type</b>", s["PatientLabel"]),
            ],
            [
                Paragraph(f"{patient.age} years / {patient.get_gender_display()}", s["PatientValue"]),
                Paragraph(patient.phone or "—", s["PatientValue"]),
                Paragraph(patient.get_payment_type_display(), s["PatientValue"]),
            ],
            [
                Spacer(1, 4),
                Spacer(1, 4),
                Spacer(1, 4),
            ],
            [
                Paragraph("<b>Requesting Doctor</b>", s["PatientLabel"]),
                Paragraph("<b>Lab Technician</b>", s["PatientLabel"]),
                Paragraph("<b>Date Completed</b>", s["PatientLabel"]),
            ],
            [
                Paragraph(doctor_name, s["PatientValue"]),
                Paragraph(tech_name, s["PatientValue"]),
                Paragraph(completed_date, s["PatientValue"]),
            ],
            [
                Spacer(1, 4),
                Spacer(1, 4),
                Spacer(1, 4),
            ],
            [
                Paragraph("<b>Date Requested</b>", s["PatientLabel"]),
                Spacer(1, 4),
                Spacer(1, 4),
            ],
            [
                Paragraph(requested_date, s["PatientValue"]),
                Spacer(1, 4),
                Spacer(1, 4),
            ],
        ]

        table = Table(data, colWidths=[col, col, col])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, BORDER),
            ("LINEBELOW", (0, 3), (-1, 3), 0.5, BORDER),
            ("LINEBELOW", (0, 6), (-1, 6), 0.5, BORDER),
            ("LINEBELOW", (0, 9), (-1, 9), 0.5, BORDER),
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
            ("BACKGROUND", (0, 3), (-1, 3), LIGHT_GRAY),
            ("BACKGROUND", (0, 6), (-1, 6), LIGHT_GRAY),
            ("BACKGROUND", (0, 9), (-1, 9), LIGHT_GRAY),
        ]))

        els = []
        els.append(Paragraph("PATIENT INFORMATION", s["SectionTitle"]))
        els.append(HRFlowable(width="100%", thickness=0.5, color=PRIMARY, spaceAfter=4))
        els.append(table)
        els.append(Spacer(1, 6))
        return els

    # ── Vitals section ──────────────────────────────────────────────

    def _build_vitals_section(self):
        triage = self.visit.triage_assessments.last()
        if not triage:
            return []

        s = self.styles
        w = self.content_width
        col = w / 4

        data = [
            [
                Paragraph("<b>Temp</b>", s["PatientLabel"]),
                Paragraph("<b>Blood Pressure</b>", s["PatientLabel"]),
                Paragraph("<b>Pulse</b>", s["PatientLabel"]),
                Paragraph("<b>O2 Sat</b>", s["PatientLabel"]),
            ],
            [
                Paragraph(f"{triage.temperature} C", s["PatientValue"]),
                Paragraph(f"{triage.blood_pressure_systolic}/{triage.blood_pressure_diastolic} mmHg", s["PatientValue"]),
                Paragraph(f"{triage.pulse} bpm", s["PatientValue"]),
                Paragraph(f"{triage.oxygen_saturation}%", s["PatientValue"]),
            ],
            [
                Spacer(1, 4),
                Spacer(1, 4),
                Spacer(1, 4),
                Spacer(1, 4),
            ],
            [
                Paragraph("<b>Weight</b>", s["PatientLabel"]),
                Paragraph("<b>Height</b>", s["PatientLabel"]),
                Spacer(1, 4),
                Spacer(1, 4),
            ],
            [
                Paragraph(f"{triage.weight} kg", s["PatientValue"]),
                Paragraph(f"{triage.height} cm", s["PatientValue"]),
                Spacer(1, 4),
                Spacer(1, 4),
            ],
        ]

        table = Table(data, colWidths=[col, col, col, col])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, BORDER),
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
            ("BACKGROUND", (0, 3), (-1, 3), LIGHT_GRAY),
        ]))

        els = []
        els.append(Paragraph("VITAL SIGNS", s["SectionTitle"]))
        els.append(HRFlowable(width="100%", thickness=0.5, color=PRIMARY, spaceAfter=4))
        els.append(table)
        els.append(Spacer(1, 6))
        return els

    # ── Tests section ───────────────────────────────────────────────

    def _build_tests_section(self):
        s = self.styles

        if not self.lab_requests:
            return [
                Paragraph("LABORATORY RESULTS", s["SectionTitle"]),
                HRFlowable(width="100%", thickness=0.5, color=PRIMARY, spaceAfter=4),
                Paragraph("No laboratory tests were requested.", s["PatientValue"]),
            ]

        els = []
        els.append(Paragraph("LABORATORY RESULTS", s["SectionTitle"]))
        els.append(HRFlowable(width="100%", thickness=0.5, color=PRIMARY, spaceAfter=6))

        for idx, req in enumerate(self.lab_requests):
            result_vals = list(
                req.result_values.select_related("parameter")
                .order_by("parameter__display_order", "parameter__name")
            )

            if result_vals:
                els.extend(self._build_structured_test(req, result_vals, idx))
            else:
                els.extend(self._build_free_text_test(req, idx))

        return els

    def _build_structured_test(self, req, result_vals, idx):
        s = self.styles
        w = self.content_width

        completed_by = req.completed_by.get_full_name() if req.completed_by else "—"
        completed_date = req.completed_at.strftime("%d %b %Y %H:%M") if req.completed_at else "—"

        els = []

        # Test name as a card header
        test_label = f"<font color='#{PRIMARY.hexval()[2:]}'>{chr(65 + idx)}.</font>  <b>{req.lab_test.name}</b>"
        if req.lab_test.unit:
            test_label += f"  <font color='#6c757d'>({req.lab_test.unit})</font>"
        els.append(Paragraph(test_label, s["TestName"]))

        # Parameter table
        headers = ["#", "Parameter", "Unit", "Reference Range", "Result", "Flag"]
        header_row = [Paragraph(h, s["TableHeaderModern"]) for h in headers]
        data = [header_row]

        for i, rv in enumerate(result_vals, 1):
            param = rv.parameter
            flag_text = ""
            flag_style = s["TableCellModern"]
            row_bg = None

            if rv.value and param.normal_min is not None and param.normal_max is not None:
                try:
                    val = float(rv.value)
                    if val < param.normal_min:
                        flag_text = "LOW"
                        flag_style = s["FlagLow"]
                        row_bg = INFO_BG
                    elif val > param.normal_max:
                        flag_text = "HIGH"
                        flag_style = s["FlagHigh"]
                        row_bg = DANGER_BG
                    else:
                        flag_text = "NORMAL"
                        flag_style = s["FlagNormal"]
                        row_bg = SUCCESS_BG
                except (ValueError, TypeError):
                    pass

            data.append([
                Paragraph(str(i), s["TableCellModern"]),
                Paragraph(f"<b>{param.name}</b>", s["TableCellBold"]),
                Paragraph(param.unit or "—", s["TableCellModern"]),
                Paragraph(param.normal_range or "—", s["TableCellModern"]),
                Paragraph(f"<b>{rv.value or '—'}</b>", s["TableCellBold"]),
                Paragraph(f"<b>{flag_text}</b>" if flag_text else "—", flag_style),
            ])

        cw = [w * x for x in (0.05, 0.18, 0.12, 0.22, 0.22, 0.21)]
        table = Table(data, colWidths=cw)

        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, PRIMARY),
        ]

        # Color the flag column cells
        for row_idx, rv in enumerate(result_vals, 1):
            param = rv.parameter
            if rv.value and param.normal_min is not None and param.normal_max is not None:
                try:
                    val = float(rv.value)
                    if val < param.normal_min:
                        style_cmds.append(("BACKGROUND", (5, row_idx), (5, row_idx), INFO_BG))
                    elif val > param.normal_max:
                        style_cmds.append(("BACKGROUND", (5, row_idx), (5, row_idx), DANGER_BG))
                    else:
                        style_cmds.append(("BACKGROUND", (5, row_idx), (5, row_idx), SUCCESS_BG))
                except (ValueError, TypeError):
                    pass

        table.setStyle(TableStyle(style_cmds))
        els.append(table)

        # Status footer
        status_color = "#198754" if req.result_status == "FINAL" else "#ffc107"
        status_label = req.get_result_status_display() if req.result_status else "Pending"
        status_line = (
            f"<font color='{status_color}'><b>{status_label}</b></font>"
            f"  <font color='#6c757d'>|</font>  "
            f"Completed by: {completed_by}"
            f"  <font color='#6c757d'>|</font>  "
            f"{completed_date}"
        )
        els.append(Spacer(1, 3))
        els.append(Paragraph(status_line, s["SmallGray"]))

        if req.remarks:
            els.append(Spacer(1, 2))
            els.append(Paragraph(f"<i>Remarks: {req.remarks}</i>", s["SmallGray"]))

        els.append(Spacer(1, 10))
        return els

    def _build_free_text_test(self, req, idx):
        s = self.styles
        w = self.content_width

        completed_by = req.completed_by.get_full_name() if req.completed_by else "—"
        completed_date = req.completed_at.strftime("%d %b %Y %H:%M") if req.completed_at else "—"

        els = []

        # Test name
        test_label = f"<font color='#{PRIMARY.hexval()[2:]}'>{chr(65 + idx)}.</font>  <b>{req.lab_test.name}</b>"
        els.append(Paragraph(test_label, s["TestName"]))

        # Result table
        data = [
            [Paragraph("<b>Result</b>", s["TableHeaderModern"]),
             Paragraph("<b>Reference Range</b>", s["TableHeaderModern"]),
             Paragraph("<b>Remarks</b>", s["TableHeaderModern"])],
            [Paragraph(req.result or "—", s["TableCellBold"]),
             Paragraph(req.lab_test.normal_range or "—", s["TableCellModern"]),
             Paragraph(req.remarks or "—", s["TableCellModern"])],
        ]

        cw = [w * 0.35, w * 0.30, w * 0.35]
        table = Table(data, colWidths=cw)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, PRIMARY),
        ]))
        els.append(table)

        # Status footer
        status_color = "#198754" if req.result_status == "FINAL" else "#ffc107"
        status_label = req.get_result_status_display() if req.result_status else "Pending"
        status_line = (
            f"<font color='{status_color}'><b>{status_label}</b></font>"
            f"  <font color='#6c757d'>|</font>  "
            f"Completed by: {completed_by}"
            f"  <font color='#6c757d'>|</font>  "
            f"{completed_date}"
        )
        els.append(Spacer(1, 3))
        els.append(Paragraph(status_line, s["SmallGray"]))
        els.append(Spacer(1, 10))

        return els


def generate_lab_report_pdf(visit_id):
    """Generate a modern A4 PDF lab report. Returns a BytesIO buffer."""
    gen = LabReportPDFGenerator(visit_id)
    return gen.generate()
