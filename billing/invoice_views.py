"""
Enhanced invoice views: preview, PDF download, DOCX download.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import HttpResponse

from billing.models import Invoice
from .invoice_services import get_invoice_data


class InvoicePreviewView(LoginRequiredMixin, View):
    """Professional invoice preview page."""

    def get(self, request, invoice_id):
        invoice = get_object_or_404(
            Invoice.objects.select_related("patient", "visit", "created_by"),
            pk=invoice_id,
        )
        data = get_invoice_data(invoice)
        return render(request, "billing/invoice_preview.html", {
            "data": data,
            "invoice": invoice,
        })


class InvoicePDFDownloadView(LoginRequiredMixin, View):
    """Download invoice as PDF."""

    def get(self, request, invoice_id):
        from .invoice_pdf import generate_invoice_pdf

        invoice = get_object_or_404(
            Invoice.objects.select_related("patient", "visit", "created_by"),
            pk=invoice_id,
        )
        data = get_invoice_data(invoice)
        pdf_buffer = generate_invoice_pdf(data)

        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        filename = f"Invoice_{invoice.invoice_number}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class InvoiceDOCXDownloadView(LoginRequiredMixin, View):
    """Download invoice as Word document."""

    def get(self, request, invoice_id):
        from .invoice_docx import generate_invoice_docx

        invoice = get_object_or_404(
            Invoice.objects.select_related("patient", "visit", "created_by"),
            pk=invoice_id,
        )
        data = get_invoice_data(invoice)
        docx_buffer = generate_invoice_docx(data)

        response = HttpResponse(
            docx_buffer,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        filename = f"Invoice_{invoice.invoice_number}.docx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class InvoicePrintView(LoginRequiredMixin, View):
    """Open printable invoice in new tab."""

    def get(self, request, invoice_id):
        invoice = get_object_or_404(
            Invoice.objects.select_related("patient", "visit", "created_by"),
            pk=invoice_id,
        )
        data = get_invoice_data(invoice)
        return render(request, "billing/invoice_print.html", {
            "data": data,
            "invoice": invoice,
        })
