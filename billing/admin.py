from django.contrib import admin
from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ("total_price",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number", "patient", "visit", "total_amount",
        "amount_paid", "status", "created_by",
    )
    list_filter = ("status",)
    search_fields = ("invoice_number", "patient__patient_number", "patient__first_name")
    readonly_fields = ("invoice_number", "total_amount", "amount_paid", "created_at", "updated_at")
    inlines = [InvoiceItemInline]


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ("invoice", "description", "quantity", "unit_price", "total_price")
    readonly_fields = ("total_price",)
