from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_number", "invoice", "amount", "payment_method",
        "reference_number", "received_by", "created_at",
    )
    list_filter = ("payment_method", "created_at")
    search_fields = (
        "receipt_number", "reference_number",
        "invoice__invoice_number", "invoice__patient__first_name",
    )
    readonly_fields = ("receipt_number", "created_at", "updated_at")
