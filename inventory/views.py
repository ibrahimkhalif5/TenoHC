from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View
from django.http import JsonResponse

from .models import Medicine, MedicineCategory, Supplier, Purchase, PurchaseItem, Stock, StockMovement
from .forms import MedicineForm, SupplierForm, PurchaseForm, PurchaseItemForm, StockAdjustForm, DispenseForm
from . import services


# ─── Dashboard ────────────────────────────────────────────────────────

class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        stats = services.get_dashboard_stats()
        low_stock = services.get_low_stock_medicines()[:5]
        expiring = services.get_expiring_medicines(30)[:5]
        return render(request, "inventory/dashboard.html", {
            "stats": stats,
            "low_stock": low_stock,
            "expiring": expiring,
        })


# ─── Medicine CRUD ────────────────────────────────────────────────────

class MedicineListView(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "")
        medicines = services.search_medicines(q)
        return render(request, "inventory/medicine_list.html", {
            "medicines": medicines,
            "query": q,
        })


class MedicineCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = MedicineForm()
        return render(request, "inventory/medicine_form.html", {"form": form, "title": "Add Medicine"})

    def post(self, request):
        form = MedicineForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Medicine added successfully.")
            return redirect("inventory:inventory-medicines")
        return render(request, "inventory/medicine_form.html", {"form": form, "title": "Add Medicine"})


class MedicineEditView(LoginRequiredMixin, View):
    def get(self, request, medicine_id):
        medicine = Medicine.objects.get(pk=medicine_id)
        form = MedicineForm(instance=medicine)
        return render(request, "inventory/medicine_form.html", {"form": form, "title": f"Edit: {medicine.name}"})

    def post(self, request, medicine_id):
        medicine = Medicine.objects.get(pk=medicine_id)
        form = MedicineForm(request.POST, instance=medicine)
        if form.is_valid():
            form.save()
            messages.success(request, "Medicine updated.")
            return redirect("inventory:inventory-medicines")
        return render(request, "inventory/medicine_form.html", {"form": form, "title": f"Edit: {medicine.name}"})


class MedicineDetailView(LoginRequiredMixin, View):
    def get(self, request, medicine_id):
        medicine = services.get_medicine(medicine_id)
        stock = services.get_stock_for_medicine(medicine_id)
        movements = services.get_stock_movements(medicine_id)[:20]
        dispense_form = DispenseForm()
        return render(request, "inventory/medicine_detail.html", {
            "medicine": medicine,
            "stock": stock,
            "movements": movements,
            "dispense_form": dispense_form,
        })


class MedicineDeleteView(LoginRequiredMixin, View):
    def post(self, request, medicine_id):
        medicine = Medicine.objects.get(pk=medicine_id)
        medicine.is_active = False
        medicine.save(update_fields=["is_active", "updated_at"])
        messages.success(request, f"{medicine.name} deactivated.")
        return redirect("inventory:inventory-medicines")


# ─── Supplier CRUD ───────────────────────────────────────────────────

class SupplierListView(LoginRequiredMixin, View):
    def get(self, request):
        suppliers = Supplier.objects.filter(is_active=True)
        return render(request, "inventory/supplier_list.html", {"suppliers": suppliers})


class SupplierCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = SupplierForm()
        return render(request, "inventory/supplier_form.html", {"form": form})

    def post(self, request):
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Supplier added.")
            return redirect("inventory:inventory-suppliers")
        return render(request, "inventory/supplier_form.html", {"form": form})


# ─── Purchase ─────────────────────────────────────────────────────────

class PurchaseListView(LoginRequiredMixin, View):
    def get(self, request):
        purchases = services.get_all_purchases()
        return render(request, "inventory/purchase_list.html", {"purchases": purchases})


class PurchaseCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = PurchaseForm()
        item_form = PurchaseItemForm()
        return render(request, "inventory/purchase_form.html", {
            "form": form, "item_form": item_form,
        })

    def post(self, request):
        form = PurchaseForm(request.POST)
        if form.is_valid():
            supplier = form.cleaned_data["supplier"]
            purchase_date = form.cleaned_data["purchase_date"]
            invoice_number = form.cleaned_data.get("invoice_number", "")
            notes = form.cleaned_data.get("notes", "")

            # Collect items from POST
            items_data = []
            medicines = request.POST.getlist("item_medicine")
            quantities = request.POST.getlist("item_quantity")
            costs = request.POST.getlist("item_unit_cost")
            batches = request.POST.getlist("item_batch_number")
            expiry_dates = request.POST.getlist("item_expiry_date")

            if not medicines:
                messages.error(request, "Please add at least one item.")
                return render(request, "inventory/purchase_form.html", {
                    "form": form, "item_form": PurchaseItemForm(),
                })

            for i in range(len(medicines)):
                items_data.append({
                    "medicine_id": int(medicines[i]),
                    "quantity": int(quantities[i]),
                    "unit_cost": costs[i],
                    "batch_number": batches[i],
                    "expiry_date": expiry_dates[i],
                })

            purchase = services.create_purchase(
                supplier_id=supplier.pk,
                purchase_date=purchase_date,
                invoice_number=invoice_number,
                items_data=items_data,
                notes=notes,
                user=request.user,
            )
            messages.success(request, f"Purchase #{purchase.pk} created. {len(items_data)} items.")
            return redirect("inventory:inventory-purchase-detail", purchase_id=purchase.pk)

        return render(request, "inventory/purchase_form.html", {
            "form": form, "item_form": PurchaseItemForm(),
        })


class PurchaseDetailView(LoginRequiredMixin, View):
    def get(self, request, purchase_id):
        purchase = services.get_purchase(purchase_id)
        return render(request, "inventory/purchase_detail.html", {"purchase": purchase})


class PurchaseReceiveView(LoginRequiredMixin, View):
    def post(self, request, purchase_id):
        try:
            purchase = services.receive_purchase(purchase_id, user=request.user)
            messages.success(
                request,
                f"Purchase #{purchase.pk} received. Stock updated for {purchase.items.count()} items.",
            )
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("inventory:inventory-purchase-detail", purchase_id=purchase_id)


class PurchaseCancelView(LoginRequiredMixin, View):
    def post(self, request, purchase_id):
        try:
            services.cancel_purchase(purchase_id, user=request.user)
            messages.success(request, "Purchase cancelled.")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("inventory:inventory-purchases")


# ─── Stock ────────────────────────────────────────────────────────────

class StockListView(LoginRequiredMixin, View):
    def get(self, request):
        stock = services.get_all_stock()
        return render(request, "inventory/stock_list.html", {"stock": stock})


class StockAdjustView(LoginRequiredMixin, View):
    def post(self, request, stock_id):
        stock = Stock.objects.get(pk=stock_id)
        form = StockAdjustForm(request.POST)
        if form.is_valid():
            services.adjust_stock(
                medicine_id=stock.medicine_id,
                batch_number=stock.batch_number,
                new_quantity=form.cleaned_data["new_quantity"],
                reason=form.cleaned_data["reason"],
                user=request.user,
            )
            messages.success(request, "Stock adjusted.")
        else:
            messages.error(request, "Failed to adjust stock.")
        return redirect("inventory:inventory-medicine-detail", medicine_id=stock.medicine_id)


class DispenseView(LoginRequiredMixin, View):
    def post(self, request, medicine_id):
        form = DispenseForm(request.POST)
        if form.is_valid():
            try:
                dispensed = services.dispense_stock(
                    medicine_id=medicine_id,
                    quantity=form.cleaned_data["quantity"],
                    reference=form.cleaned_data.get("reference", ""),
                    notes=form.cleaned_data.get("notes", ""),
                    user=request.user,
                )
                total = sum(q for _, q in dispensed)
                messages.success(request, f"Dispensed {total} units across {len(dispensed)} batch(es).")
            except ValueError as e:
                messages.error(request, str(e))
        return redirect("inventory:inventory-medicine-detail", medicine_id=medicine_id)


# ─── Alerts ───────────────────────────────────────────────────────────

class LowStockView(LoginRequiredMixin, View):
    def get(self, request):
        medicines = services.get_low_stock_medicines()
        medicines_with_shortage = []
        for m in medicines:
            m.shortage = max(0, (m.minimum_stock or 0) - (m.total_stock or 0))
            medicines_with_shortage.append(m)
        return render(request, "inventory/low_stock.html", {"medicines": medicines_with_shortage})


class ExpiringView(LoginRequiredMixin, View):
    def get(self, request):
        expiring = services.get_expiring_medicines(30)
        expired = services.get_expired_stock()
        return render(request, "inventory/expiring.html", {
            "expiring": expiring,
            "expired": expired,
        })


# ─── Movement History ────────────────────────────────────────────────

class MovementHistoryView(LoginRequiredMixin, View):
    def get(self, request):
        medicine_id = request.GET.get("medicine_id")
        movements = services.get_stock_movements(medicine_id)
        return render(request, "inventory/movements.html", {
            "movements": movements,
            "medicine_id": medicine_id,
        })


# ─── API ──────────────────────────────────────────────────────────────

class MedicineSearchAPIView(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "")
        medicines = services.search_medicines(q)
        data = [
            {"id": m.id, "name": str(m), "selling_price": str(m.selling_price),
             "current_stock": m.total_stock,
             "strength": m.strength or "",
             "dosage_form": m.get_dosage_form_display() if m.dosage_form else ""}
            for m in medicines
        ]
        return JsonResponse({"results": data})


class MedicineResolveAPIView(LoginRequiredMixin, View):
    """Resolve an Item Master MEDICINE item to an inventory.Medicine record.
    Finds by name match or creates a new Medicine linked to the Item."""
    def get(self, request):
        item_id = request.GET.get("item_id")
        if not item_id:
            return JsonResponse({"error": "No item_id"}, status=400)
        try:
            from core.models import Item
            item = Item.objects.get(pk=item_id, is_active=True)
        except (Item.DoesNotExist, ValueError):
            return JsonResponse({"error": "Item not found"}, status=404)

        medicine = Medicine.objects.filter(item=item).first()
        if not medicine:
            medicine = Medicine.objects.filter(name__iexact=item.name).first()
        if not medicine:
            medicine = Medicine.objects.create(
                item=item,
                name=item.name,
                selling_price=item.unit_price,
                cost_price=item.cost_price,
                description=item.description,
            )
        elif not medicine.item:
            medicine.item = item
            if medicine.selling_price != item.unit_price:
                medicine.selling_price = item.unit_price
            medicine.save(update_fields=["item", "selling_price", "updated_at"])

        return JsonResponse({
            "id": medicine.pk,
            "name": str(medicine),
            "selling_price": str(medicine.selling_price),
        })
