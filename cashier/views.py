from billing.models import Invoice
from billing.services import get_invoice
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View

from .forms import PaymentForm
from . import services


class InvoiceListView(LoginRequiredMixin, View):
    """List all invoices with balances."""

    def get(self, request):
        invoices = (
            Invoice.objects
            .select_related("patient", "visit")
            .order_by("-created_at")
        )
        status_filter = request.GET.get("status", "")
        if status_filter:
            invoices = invoices.filter(status=status_filter)
        return render(request, "billing/invoice_list.html", {
            "invoices": invoices,
            "status_filter": status_filter,
        })


class InvoiceDetailView(LoginRequiredMixin, View):
    """View invoice details with line items and payment history."""

    def get(self, request, invoice_id):
        invoice = get_object_or_404(
            Invoice.objects.select_related("patient", "visit").prefetch_related("items"),
            pk=invoice_id,
        )
        payments = services.get_invoice_payments(invoice_id)
        return render(request, "billing/invoice_detail.html", {
            "invoice": invoice,
            "payments": payments,
        })


class PaymentCreateView(LoginRequiredMixin, View):
    """Process a payment for an invoice."""

    def get(self, request, invoice_id):
        invoice = get_invoice(invoice_id)
        form = PaymentForm(max_amount=invoice.balance)
        return render(request, "cashier/process_payment.html", {
            "invoice": invoice,
            "form": form,
        })

    def post(self, request, invoice_id):
        invoice = get_invoice(invoice_id)
        form = PaymentForm(request.POST, max_amount=invoice.balance)
        if form.is_valid():
            try:
                payment = services.process_payment(
                    invoice_id=invoice_id,
                    amount=form.cleaned_data["amount"],
                    payment_method=form.cleaned_data["payment_method"],
                    reference_number=form.cleaned_data.get("reference_number", ""),
                    user=request.user,
                )
                messages.success(
                    request,
                    f"Payment of KSh {payment.amount:,.2f} received. Receipt: {payment.receipt_number}",
                )
                return redirect("cashier:cashier-receipt", payment_id=payment.pk)
            except ValueError as e:
                messages.error(request, str(e))
        return render(request, "cashier/process_payment.html", {
            "invoice": invoice,
            "form": form,
        })


class ReceiptView(LoginRequiredMixin, View):
    """View/print a receipt."""

    def get(self, request, payment_id):
        payment = services.get_payment(payment_id)
        return render(request, "cashier/receipt.html", {
            "payment": payment,
        })


class PaymentHistoryView(LoginRequiredMixin, View):
    """View all payments."""

    def get(self, request):
        payments = services.get_all_payments()
        return render(request, "cashier/payment_history.html", {
            "payments": payments,
        })


class OutstandingView(LoginRequiredMixin, View):
    """View outstanding balances."""

    def get(self, request):
        invoices = services.get_pending_invoices()
        summary = services.get_outstanding_summary()
        return render(request, "cashier/outstanding.html", {
            "invoices": invoices,
            "summary": summary,
        })


class CashierDashboardView(LoginRequiredMixin, View):
    """Cashier main page: pending invoices + quick stats."""

    def get(self, request):
        from django.db.models import Sum, Count
        pending = services.get_pending_invoices()
        summary = services.get_outstanding_summary()
        recent_payments = services.get_all_payments()[:10]
        return render(request, "cashier/dashboard.html", {
            "pending_invoices": pending,
            "pending_count": pending.count(),
            "summary": summary,
            "recent_payments": recent_payments,
        })
