"""
Professional PDF generation for patient invoices using ReportLab.
"""
import os
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from core.document_service import DocumentTemplateService
from core.constants import CASHIER_NAME, DOCTOR_NAME


class InvoicePDFGenerator(DocumentTemplateService):
    """Generate professional A4 PDF invoices."""

    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self.data = data
        self.invoice = data["invoice"]
        self.patient = data["patient"]

    def get_title(self):
        return "PATIENT INVOICE"

    def build_elements(self):
        els = []
        els.extend(self.build_hospital_header())
        els.extend(self.build_title_block())
        els.extend(self._build_invoice_patient_info())
        els.extend(self._build_visit_info())
        els.extend(self._build_diagnosis())
        els.extend(self._build_services())
        els.extend(self._build_lab_tests())
        els.extend(self._build_radiology())
        els.extend(self._build_medications())
        els.extend(self._build_ward_info())
        els.extend(self._build_nursing())
        els.extend(self._build_other_charges())
        els.extend(self._build_bill_summary())
        els.extend(self._build_payment_history())
        els.extend(self._build_footer_message())
        return els

    def _build_invoice_patient_info(self):
        s = self.styles
        data = self.data
        cw = self.content_width
        half = cw / 2

        inv_rows = [
            self.build_kv_row("Invoice Number", data["invoice"].invoice_number),
            self.build_kv_row("Visit Number", data["invoice"].visit.visit_number),
            self.build_kv_row("Invoice Date",
                data["invoice"].created_at.strftime("%d %b %Y %H:%M") if data["invoice"].created_at else "—"),
            self.build_kv_row("Cashier", CASHIER_NAME),
            self.build_kv_row("Payment Status", data["invoice"].get_status_display()),
        ]
        pat_rows = [
            self.build_kv_row("Patient Name", data["patient"].full_name),
            self.build_kv_row("Patient Number", data["patient"].patient_number),
            self.build_kv_row("Gender", data["patient"].get_gender_display()),
            self.build_kv_row("Age", f"{data['patient'].age} years"),
            self.build_kv_row("Phone", data["patient"].phone),
            self.build_kv_row("National ID", data["patient"].national_id or "—"),
            self.build_kv_row("Category", str(data["patient"].patient_category) if data["patient"].patient_category else "—"),
            self.build_kv_row("Payment Type", data["patient"].get_payment_type_display()),
        ]

        left = self.build_kv_table(inv_rows, [half, half])
        right = self.build_kv_table(pat_rows, [half, half])
        outer = Table([[left, right]], colWidths=[half + 4, half + 4])
        outer.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))

        els = []
        els.extend(self.build_section_heading("INVOICE & PATIENT INFORMATION"))
        els.append(outer)
        els.append(Spacer(1, 6))
        return els

    def _build_visit_info(self):
        data = self.data
        rows = [
            self.build_kv_row("Registration Date",
                data["invoice"].visit.visit_date.strftime("%d %b %Y") if data["invoice"].visit.visit_date else "—"),
            self.build_kv_row("Consultation Date",
                data["consultation"].created_at.strftime("%d %b %Y") if data["consultation"] else "—"),
            self.build_kv_row("Visit Type", data["visit_type"]),
            self.build_kv_row("Attending Doctor", DOCTOR_NAME),
        ]
        if data["admission"]:
            adm = data["admission"]
            rows.append(self.build_kv_row("Admission Date", adm.admission_date.strftime("%d %b %Y") if adm.admission_date else "—"))
            rows.append(self.build_kv_row("Discharge Date", adm.discharge_date.strftime("%d %b %Y") if adm.discharge_date else "Currently Admitted"))
            rows.append(self.build_kv_row("Ward", f"{adm.ward.name} ({adm.ward.get_ward_type_display()})"))
            rows.append(self.build_kv_row("Room / Bed", f"{adm.room.room_number} / {adm.bed.bed_number}"))

        els = []
        els.extend(self.build_section_heading("VISIT INFORMATION"))
        els.append(self.build_kv_table(rows))
        els.append(Spacer(1, 6))
        return els

    def _build_diagnosis(self):
        data = self.data
        if not data["primary_diagnosis"] and not data["secondary_diagnosis"]:
            return []
        rows = [self.build_kv_row("Primary Diagnosis", data["primary_diagnosis"])]
        if data["secondary_diagnosis"]:
            rows.append(self.build_kv_row("Secondary Diagnosis", data["secondary_diagnosis"]))
        els = []
        els.extend(self.build_section_heading("DIAGNOSIS"))
        els.append(self.build_kv_table(rows))
        els.append(Spacer(1, 6))
        return els

    def _build_services(self):
        data = self.data
        if not data["services"]:
            return []
        cw = self.content_width
        headers = ["Date", "Department", "Service", "Qty", "Unit Price", "Amount"]
        rows = [[s["date"], s["department"], s["service"], str(s["quantity"]),
                 self.money(s["unit_price"]), self.money(s["amount"])] for s in data["services"]]
        widths = [cw*0.13, cw*0.14, cw*0.33, cw*0.08, cw*0.16, cw*0.16]
        els = []
        els.extend(self.build_section_heading("SERVICES PROVIDED"))
        els.append(self.build_data_table(headers, rows, widths))
        els.append(Spacer(1, 6))
        return els

    def _build_lab_tests(self):
        data = self.data
        if not data["lab_tests"]:
            return []
        cw = self.content_width
        headers = ["Test Name", "Qty", "Unit Price", "Amount", "Status"]
        rows = [[l["test_name"], str(l["quantity"]), self.money(l["unit_price"]),
                 self.money(l["amount"]), l["status"]] for l in data["lab_tests"]]
        widths = [cw*0.35, cw*0.1, cw*0.2, cw*0.2, cw*0.15]
        els = []
        els.extend(self.build_section_heading("LABORATORY TESTS"))
        els.append(self.build_data_table(headers, rows, widths))
        els.append(Spacer(1, 6))
        return els

    def _build_radiology(self):
        data = self.data
        if not data["radiology"]:
            return []
        cw = self.content_width
        headers = ["Service", "Qty", "Unit Price", "Amount"]
        rows = [[r["service"], str(r["quantity"]), self.money(r["unit_price"]),
                 self.money(r["amount"])] for r in data["radiology"]]
        widths = [cw*0.4, cw*0.1, cw*0.25, cw*0.25]
        els = []
        els.extend(self.build_section_heading("RADIOLOGY / IMAGING"))
        els.append(self.build_data_table(headers, rows, widths))
        els.append(Spacer(1, 6))
        return els

    def _build_medications(self):
        data = self.data
        if not data["medications"]:
            return []
        cw = self.content_width
        headers = ["Medicine", "Dosage", "Qty", "Unit Price", "Amount"]
        rows = [[m["medicine_name"], m.get("dosage", ""), str(m["quantity"]),
                 self.money(m["unit_price"]), self.money(m["amount"])] for m in data["medications"]]
        widths = [cw*0.3, cw*0.15, cw*0.1, cw*0.22, cw*0.23]
        els = []
        els.extend(self.build_section_heading("MEDICATIONS"))
        els.append(self.build_data_table(headers, rows, widths))
        els.append(Spacer(1, 6))
        return els

    def _build_ward_info(self):
        data = self.data
        if not data["ward"]:
            return []
        w = data["ward"]
        rows = [
            self.build_kv_row("Ward Type", w["ward_type"]),
            self.build_kv_row("Room Number", w["room_number"]),
            self.build_kv_row("Bed Number", w["bed_number"]),
            self.build_kv_row("Admission Date", w["admission_date"]),
            self.build_kv_row("Discharge Date", w["discharge_date"]),
            self.build_kv_row("Length of Stay", f"{w['length_of_stay']} night(s)"),
            self.build_kv_row("Rate Per Night", self.money(w["ward_rate"])),
            self.build_kv_row("Total Ward Charges", self.money(w["total_charges"])),
        ]
        els = []
        els.extend(self.build_section_heading("WARD INFORMATION"))
        els.append(self.build_kv_table(rows))
        els.append(Spacer(1, 6))
        return els

    def _build_nursing(self):
        data = self.data
        if not data["nursing"]:
            return []
        cw = self.content_width
        headers = ["Service", "Qty", "Unit Price", "Amount"]
        rows = [[n["service"], str(n["quantity"]), self.money(n["unit_price"]),
                 self.money(n["amount"])] for n in data["nursing"]]
        widths = [cw*0.45, cw*0.1, cw*0.22, cw*0.23]
        els = []
        els.extend(self.build_section_heading("NURSING SERVICES"))
        els.append(self.build_data_table(headers, rows, widths))
        els.append(Spacer(1, 6))
        return els

    def _build_other_charges(self):
        data = self.data
        if not data["other_charges"]:
            return []
        cw = self.content_width
        headers = ["Service", "Qty", "Unit Price", "Amount"]
        rows = [[o["service"], str(o["quantity"]), self.money(o["unit_price"]),
                 self.money(o["amount"])] for o in data["other_charges"]]
        widths = [cw*0.45, cw*0.1, cw*0.22, cw*0.23]
        els = []
        els.extend(self.build_section_heading("OTHER CHARGES"))
        els.append(self.build_data_table(headers, rows, widths))
        els.append(Spacer(1, 6))
        return els

    def _build_bill_summary(self):
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT
        sm = self.data["summary"]
        s = self.styles
        cw = self.content_width

        TC = ParagraphStyle("TC", parent=s["Normal"], fontSize=8.5, leading=11,
                           textColor=colors.HexColor("#212529"), fontName="Helvetica")
        TC_GREEN = ParagraphStyle("TCG", parent=s["Normal"], fontSize=8.5, leading=11,
                           textColor=colors.HexColor("#198754"), fontName="Helvetica")

        sum_rows = []
        for label, val in [
            ("Registration Fee", sm["registration_fee"]),
            ("Consultation Fee", sm["consultation_fee"]),
            ("Laboratory Charges", sm["lab_charges"]),
            ("Radiology Charges", sm["radiology_charges"]),
            ("Medication Charges", sm["medication_charges"]),
            ("Ward Charges", sm["ward_charges"]),
            ("Nursing Charges", sm["nursing_charges"]),
            ("Procedure Charges", sm["procedure_charges"]),
            ("Other Charges", sm["other_charges"]),
        ]:
            if val and val > 0:
                sum_rows.append([Paragraph(label, TC), Paragraph(self.money(val), TC)])

        sum_rows.append([Paragraph("<b>Total Hospital Bill</b>", TC), Paragraph(f"<b>{self.money(sm['grand_total'])}</b>", TC)])
        sum_rows.append([Paragraph("<b>Amount Paid</b>", TC), Paragraph(f"<b>{self.money(sm['amount_paid'])}</b>", TC)])
        sum_rows.append([Paragraph("<b>Outstanding Before Rebate</b>", TC), Paragraph(f"<b>{self.money(sm['outstanding_before_rebate'])}</b>", TC)])
        if sm["nhif_bed_rebate"] > 0:
            sum_rows.append([Paragraph(f"<b>NHIF/SHA Bed Rebate ({sm['nights_stayed']} nights &times; {self.money(sm['rebate_per_night'])}/night)</b>", TC),
                             Paragraph(f"<b style='color:#198754'>- {self.money(sm['nhif_bed_rebate'])}</b>", TC_GREEN)])
        bal_color = "#dc3545" if sm["balance"] > 0 else "#198754"
        sum_rows.append([Paragraph("<b>Final Balance</b>", TC),
                         Paragraph(f"<b style='color:{bal_color}'>{self.money(sm['balance'])}</b>", TC)])

        sw = cw * 0.55
        from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle
        sum_tbl = RLTable(sum_rows, colWidths=[sw, sw])
        sum_tbl.setStyle(RLTableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dee2e6")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
            ("LINEABOVE", (0, -3), (-1, -3), 1, colors.HexColor("#0d6efd")),
            ("BACKGROUND", (0, -3), (-1, -3), colors.HexColor("#e7f1ff")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fff5f5") if sm["balance"] > 0 else colors.HexColor("#f0fff4")),
        ]))
        els = []
        els.extend(self.build_section_heading("BILL SUMMARY"))
        els.append(sum_tbl)
        els.append(Spacer(1, 8))
        return els

    def _build_payment_history(self):
        data = self.data
        if not data["payments"]:
            return []
        cw = self.content_width
        headers = ["Date", "Receipt #", "Method", "Amount", "Cashier"]
        rows = [[p["date"], p["receipt_number"], p["payment_method"],
                 self.money(p["amount"]), p["cashier"]] for p in data["payments"]]
        widths = [cw*0.2, cw*0.2, cw*0.15, cw*0.2, cw*0.25]
        els = []
        els.extend(self.build_section_heading("PAYMENT HISTORY"))
        els.append(self.build_data_table(headers, rows, widths))
        els.append(Spacer(1, 8))
        return els

    def _build_footer_message(self):
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        s = self.styles
        center_small = ParagraphStyle("CenterSmall", parent=s["Normal"], fontSize=7, leading=9,
                                     alignment=TA_CENTER, textColor=colors.HexColor("#8b919a"),
                                     fontName="Helvetica-Oblique")
        return [
            Spacer(1, 6),
            Paragraph("Thank you for choosing TENOCARE HOSPITAL.", center_small),
            Paragraph("Please retain this invoice for future reference.", center_small),
        ]


# Re-export old function signature for backward compatibility
def generate_invoice_pdf(data):
    """Generate a professional A4 PDF invoice. Returns a BytesIO buffer."""
    gen = InvoicePDFGenerator(data)
    return gen.generate()
