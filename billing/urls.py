from django.urls import path
from . import views
from . import invoice_views

app_name = "billing"

urlpatterns = [
    path("", views.BillingIndexView.as_view(), name="billing-list"),
    path("invoice/<int:invoice_id>/preview/", invoice_views.InvoicePreviewView.as_view(), name="invoice-preview"),
    path("invoice/<int:invoice_id>/pdf/", invoice_views.InvoicePDFDownloadView.as_view(), name="invoice-pdf"),
    path("invoice/<int:invoice_id>/docx/", invoice_views.InvoiceDOCXDownloadView.as_view(), name="invoice-docx"),
    path("invoice/<int:invoice_id>/print/", invoice_views.InvoicePrintView.as_view(), name="invoice-print"),
]
