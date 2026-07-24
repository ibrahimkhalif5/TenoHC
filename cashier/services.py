"""
Service layer for cashier app.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import Payment
from billing.models import Invoice


def generate_receipt_number():
    """Generate unique receipt number: RCP-YYYY-NNNNNN."""
    from datetime import date
    year = date.today().year
    prefix = f"RCP-{year}-"

    with transaction.atomic():
        last = (
            Payment.objects
            .select_for_update()
            .filter(receipt_number__startswith=prefix)
            .order_by("-receipt_number")
            .first()
        )
        if last:
            last_seq = int(last.receipt_number.split("-")[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1
        return f"{prefix}{next_seq:06d}"


def process_payment(invoice_id, amount, payment_method, reference_number="", user=None):
    """
    Process a payment against an invoice.
    Updates invoice amount_paid and status.
    Returns the Payment object.
    """
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)

        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero")

        if invoice.status == Invoice.Status.PAID:
            raise ValueError("Invoice is already fully paid")

        if amount > invoice.balance:
            raise ValueError(
                f"Payment amount (KSh {amount:,.2f}) exceeds outstanding balance (KSh {invoice.balance:,.2f})"
            )

        payment = Payment.objects.create(
            invoice=invoice,
            amount=amount,
            payment_method=payment_method,
            reference_number=reference_number,
            receipt_number=generate_receipt_number(),
            received_by=user,
        )

        # Update invoice
        invoice.amount_paid = Decimal(str(invoice.amount_paid)) + Decimal(str(amount))
        if invoice.amount_paid >= invoice.total_amount:
            invoice.status = Invoice.Status.PAID
        else:
            invoice.status = Invoice.Status.PARTIALLY_PAID
        invoice.save(update_fields=["amount_paid", "status", "updated_at"])

        return payment


def get_pending_invoices():
    """Get all invoices with outstanding balance."""
    return (
        Invoice.objects
        .filter(status__in=[Invoice.Status.PENDING, Invoice.Status.PARTIALLY_PAID])
        .select_related("patient", "visit")
        .order_by("-created_at")
    )


def get_invoice_payments(invoice_id):
    """Get all payments for an invoice."""
    return Payment.objects.filter(invoice_id=invoice_id).select_related("received_by", "invoice__patient")


def get_payment(payment_id):
    """Get a payment with invoice and patient."""
    return (
        Payment.objects
        .select_related("invoice", "invoice__patient", "invoice__visit", "received_by")
        .get(pk=payment_id)
    )


def get_all_payments():
    """Get all payments (payment history)."""
    return (
        Payment.objects
        .select_related("invoice", "invoice__patient", "invoice__visit", "received_by")
        .order_by("-created_at")
    )


def get_outstanding_summary():
    """Get summary of outstanding balances."""
    from django.db.models import Sum, Count, Value
    from decimal import Decimal
    result = (
        Invoice.objects
        .filter(status__in=[Invoice.Status.PENDING, Invoice.Status.PARTIALLY_PAID])
        .aggregate(
            total_outstanding=Sum("total_amount", default=Decimal("0")) - Sum("amount_paid", default=Decimal("0")),
            count=Count("id"),
        )
    )
    if result["total_outstanding"] is None:
        result["total_outstanding"] = Decimal("0")
    return result
