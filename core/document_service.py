"""
Reusable DocumentTemplateService base class for PDF and DOCX generation.
Provides shared hospital header, footer, and styling utilities for all
document generators (discharge summary, invoices, etc.).
"""
import io
import os
from abc import ABC, abstractmethod

from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable,
)
from reportlab.platypus.flowables import Flowable


# ── Page constants ──────────────────────────────────────────────────
PAGE_WIDTH, PAGE_HEIGHT = A4
DEFAULT_LEFT_MARGIN = 1.5 * cm
DEFAULT_RIGHT_MARGIN = 1.5 * cm
DEFAULT_TOP_MARGIN = 1.5 * cm
DEFAULT_BOTTOM_MARGIN = 2.5 * cm


class DocumentTemplateService(ABC):
    """
    Abstract base class for document generation.

    Subclasses must implement:
        - build_elements() -> list of ReportLab flowables
        - get_title() -> document title string
    """

    def __init__(self, left_margin=None, right_margin=None,
                 top_margin=None, bottom_margin=None):
        self.left_margin = left_margin or DEFAULT_LEFT_MARGIN
        self.right_margin = right_margin or DEFAULT_RIGHT_MARGIN
        self.top_margin = top_margin or DEFAULT_TOP_MARGIN
        self.bottom_margin = bottom_margin or DEFAULT_BOTTOM_MARGIN
        self.content_width = PAGE_WIDTH - self.left_margin - self.right_margin
        self._styles = None
        self._hospital = None

    # ── Public API ──────────────────────────────────────────────────

    def generate(self):
        """Generate the PDF and return a BytesIO buffer."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=self.left_margin,
            rightMargin=self.right_margin,
            topMargin=self.top_margin,
            bottomMargin=self.bottom_margin,
        )

        elements = self.build_elements()
        doc.build(elements, onFirstPage=self._footer, onLaterPages=self._footer)
        buffer.seek(0)
        return buffer

    @abstractmethod
    def build_elements(self):
        """Return a list of ReportLab flowables for the document body."""
        ...

    @abstractmethod
    def get_title(self):
        """Return the document title string (e.g., 'DISCHARGE SUMMARY')."""
        ...

    # ── Hospital data ───────────────────────────────────────────────

    @property
    def hospital(self):
        if self._hospital is None:
            from core.models import HospitalSetting
            self._hospital = HospitalSetting.load()
        return self._hospital

    # ── Hospital header ─────────────────────────────────────────────

    def build_hospital_header(self):
        """Build the hospital logo + name + contact block."""
        els = []
        hospital = self.hospital

        if hospital.logo and os.path.exists(hospital.logo.path):
            try:
                img = Image(hospital.logo.path, width=50, height=50)
                img.hAlign = "LEFT"
                els.append(img)
            except Exception:
                pass

        els.append(Paragraph(hospital.name, self.styles["HospitalName"]))
        if hospital.address:
            els.append(Paragraph(hospital.address, self.styles["HospitalInfo"]))

        contact_parts = []
        if hospital.telephone:
            contact_parts.append(f"Tel: {hospital.telephone}")
        if hospital.email:
            contact_parts.append(f"Email: {hospital.email}")
        if contact_parts:
            els.append(Paragraph(" | ".join(contact_parts), self.styles["HospitalInfo"]))

        els.append(Spacer(1, 6))
        els.append(HRFlowable(
            width="100%", thickness=1.5,
            color=colors.HexColor("#0d6efd"),
            spaceAfter=6,
        ))

        return els

    def build_title_block(self):
        """Build the document title + divider line."""
        els = []
        els.append(Paragraph(self.get_title(), self.styles["DocTitle"]))
        els.append(HRFlowable(
            width="100%", thickness=0.5,
            color=colors.HexColor("#dee2e6"),
            spaceAfter=8,
        ))
        return els

    # ── Styles ──────────────────────────────────────────────────────

    @property
    def styles(self):
        if self._styles is None:
            self._styles = self._build_styles()
        return self._styles

    def _build_styles(self):
        """Build the base paragraph styles. Override to add custom styles."""
        s = getSampleStyleSheet()

        s.add(ParagraphStyle(
            name="HospitalName",
            parent=s["Title"],
            fontSize=16, leading=20, alignment=TA_CENTER,
            spaceAfter=2,
            textColor=colors.HexColor("#1a1d21"),
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="HospitalInfo",
            parent=s["Normal"],
            fontSize=8, leading=10, alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
        ))
        s.add(ParagraphStyle(
            name="DocTitle",
            parent=s["Title"],
            fontSize=13, leading=16, alignment=TA_CENTER,
            spaceBefore=6, spaceAfter=6,
            textColor=colors.HexColor("#0d6efd"),
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="SectionHeading",
            parent=s["Heading2"],
            fontSize=10, leading=13,
            spaceBefore=10, spaceAfter=4,
            textColor=colors.HexColor("#0d6efd"),
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="FieldLabel",
            parent=s["Normal"],
            fontSize=8, leading=10,
            textColor=colors.HexColor("#6c757d"),
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="FieldValue",
            parent=s["Normal"],
            fontSize=9, leading=12,
            textColor=colors.HexColor("#212529"),
            fontName="Helvetica",
        ))
        s.add(ParagraphStyle(
            name="FieldValueSmall",
            parent=s["Normal"],
            fontSize=8, leading=10,
            textColor=colors.HexColor("#212529"),
            fontName="Helvetica",
        ))
        s.add(ParagraphStyle(
            name="TableCell",
            parent=s["Normal"],
            fontSize=8, leading=10,
            textColor=colors.HexColor("#212529"),
            fontName="Helvetica",
        ))
        s.add(ParagraphStyle(
            name="TableHeader",
            parent=s["Normal"],
            fontSize=8, leading=10,
            textColor=colors.white,
            fontName="Helvetica-Bold",
        ))
        s.add(ParagraphStyle(
            name="Footer",
            parent=s["Normal"],
            fontSize=7, leading=9, alignment=TA_CENTER,
            textColor=colors.HexColor("#8b919a"),
            fontName="Helvetica-Oblique",
        ))
        s.add(ParagraphStyle(
            name="Right",
            parent=s["Normal"],
            fontSize=8.5, leading=11, alignment=TA_RIGHT,
            textColor=colors.HexColor("#212529"),
            fontName="Helvetica",
        ))

        return s

    # ── Reusable building blocks ────────────────────────────────────

    def build_section_heading(self, title):
        """Return a colored section heading + divider."""
        return [
            Paragraph(title, self.styles["SectionHeading"]),
            HRFlowable(width="100%", thickness=0.5,
                       color=colors.HexColor("#dee2e6"), spaceAfter=4),
        ]

    def build_kv_table(self, rows, col_widths=None):
        """Build a bordered key-value info table."""
        if col_widths is None:
            col_widths = [self.content_width * 0.35, self.content_width * 0.65]
        table = Table(rows, colWidths=col_widths)
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8f9fa")),
        ]))
        return table

    def build_kv_row(self, label, value):
        """Return a single label-value row for a KV table."""
        return [
            Paragraph(f"<b>{label}:</b>", self.styles["FieldLabel"]),
            Paragraph(str(value) if value else "—", self.styles["FieldValue"]),
        ]

    def build_data_table(self, headers, rows, col_widths):
        """Build a data table with colored header row."""
        data = [[Paragraph(h, self.styles["TableHeader"]) for h in headers]]
        for row in rows:
            data.append([Paragraph(str(c), self.styles["TableCell"]) for c in row])
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f8f9fa")]),
        ]))
        return table

    def build_text_block(self, label, text):
        """Return a label + text block with spacing."""
        return [
            Paragraph(f"<b>{label}</b>", self.styles["FieldLabel"]),
            Paragraph(text if text else "—", self.styles["FieldValue"]),
            Spacer(1, 4),
        ]

    def money(self, val):
        """Format a value as KES currency."""
        if val is None:
            return "—"
        return f"KSh {val:,.2f}"

    # ── Footer ──────────────────────────────────────────────────────

    def _footer(self, canvas, doc):
        canvas.saveState()
        footer_text = (
            "This document was generated electronically by the "
            "TENOCARE HOSPITAL Information Management System."
        )
        canvas.setFont("Helvetica-Oblique", 7)
        canvas.setFillColor(colors.HexColor("#8b919a"))
        canvas.drawCentredString(PAGE_WIDTH / 2, 1.2 * cm, footer_text)
        canvas.drawRightString(
            PAGE_WIDTH - self.right_margin, 1.2 * cm,
            f"Page {canvas.getPageNumber()}",
        )
        canvas.restoreState()


# ── Helper: SectionDivider flowable ─────────────────────────────────

class SectionDivider(Flowable):
    """A thin horizontal line used to visually separate sections."""

    def __init__(self, width, color=colors.HexColor("#dee2e6")):
        Flowable.__init__(self)
        self.width = width
        self.color = color
        self.height = 6

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(0.5)
        self.canv.line(0, 3, self.width, 3)
