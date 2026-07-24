from django.contrib import admin
from .models import MedicineCategory, Supplier, Medicine, Purchase, PurchaseItem, Stock, StockMovement


@admin.register(MedicineCategory)
class MedicineCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_editable = ("is_active",)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_person", "phone", "email", "is_active")
    list_editable = ("is_active",)
    search_fields = ("name",)


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = (
        "name", "generic_name", "category", "dosage_form", "strength",
        "selling_price", "minimum_stock", "is_active",
    )
    list_filter = ("category", "dosage_form", "is_active")
    search_fields = ("name", "generic_name")
    list_editable = ("selling_price", "minimum_stock", "is_active")


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0
    readonly_fields = ("total_cost",)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("pk", "supplier", "purchase_date", "invoice_number", "total_amount", "status")
    list_filter = ("status",)
    inlines = [PurchaseItemInline]


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("medicine", "batch_number", "quantity", "expiry_date", "purchase_price")
    list_filter = ("medicine__category",)
    search_fields = ("medicine__name", "batch_number")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("medicine", "movement_type", "quantity", "batch_number", "reference", "created_by", "created_at")
    list_filter = ("movement_type",)
    search_fields = ("medicine__name", "reference")
    readonly_fields = ("created_at",)
