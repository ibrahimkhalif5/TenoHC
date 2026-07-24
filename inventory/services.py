"""
Service layer for inventory app.
"""
from datetime import date
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q, F

from .models import Medicine, MedicineCategory, Supplier, Purchase, PurchaseItem, Stock, StockMovement


# ─── Medicine ─────────────────────────────────────────────────────────

def get_all_medicines():
    return Medicine.objects.filter(is_active=True).select_related("category").annotate(
        total_stock=Sum("stocks__quantity"),
    )


def search_medicines(query):
    if not query:
        return get_all_medicines()
    return Medicine.objects.filter(
        Q(name__icontains=query) | Q(generic_name__icontains=query) | Q(category__name__icontains=query),
        is_active=True,
    ).select_related("category").annotate(
        total_stock=Sum("stocks__quantity"),
    )


def get_medicine(medicine_id):
    return Medicine.objects.select_related("category").get(pk=medicine_id)


# ─── Stock ────────────────────────────────────────────────────────────

def get_stock_for_medicine(medicine_id):
    return Stock.objects.filter(
        medicine_id=medicine_id, quantity__gt=0,
    ).order_by("expiry_date")


def get_all_stock():
    return Stock.objects.filter(
        quantity__gt=0,
    ).select_related("medicine", "medicine__category").order_by("medicine__name", "expiry_date")


def get_low_stock_medicines():
    """Get medicines where current stock < minimum_stock."""
    medicines = Medicine.objects.filter(is_active=True).annotate(
        total_stock=Sum("stocks__quantity"),
    )
    return medicines.filter(
        Q(total_stock__lt=F("minimum_stock")) | Q(total_stock__isnull=True),
    ).select_related("category")


def get_expiring_medicines(days=30):
    """Get stock batches expiring within N days."""
    from datetime import timedelta
    threshold = date.today() + timedelta(days=days)
    return Stock.objects.filter(
        expiry_date__lte=threshold,
        expiry_date__gte=date.today(),
        quantity__gt=0,
    ).select_related("medicine").order_by("expiry_date")


def get_expired_stock():
    """Get stock that is already expired."""
    return Stock.objects.filter(
        expiry_date__lt=date.today(),
        quantity__gt=0,
    ).select_related("medicine").order_by("expiry_date")


# ─── Purchase ─────────────────────────────────────────────────────────

def get_all_purchases():
    return Purchase.objects.select_related("supplier", "received_by").prefetch_related("items__medicine")


def get_purchase(purchase_id):
    return Purchase.objects.select_related("supplier", "received_by").prefetch_related("items__medicine").get(pk=purchase_id)


def create_purchase(supplier_id, purchase_date, invoice_number, items_data, notes="", user=None):
    """
    Create a purchase order.
    items_data: list of dicts with keys: medicine_id, quantity, unit_cost, batch_number, expiry_date
    """
    with transaction.atomic():
        supplier = Supplier.objects.get(pk=supplier_id)
        purchase = Purchase.objects.create(
            supplier=supplier,
            purchase_date=purchase_date,
            invoice_number=invoice_number,
            notes=notes,
            received_by=user,
        )

        for item in items_data:
            medicine = Medicine.objects.get(pk=item["medicine_id"])
            PurchaseItem.objects.create(
                purchase=purchase,
                medicine=medicine,
                quantity=item["quantity"],
                unit_cost=item["unit_cost"],
                batch_number=item.get("batch_number", ""),
                expiry_date=item["expiry_date"],
            )

        return purchase


def receive_purchase(purchase_id, user=None):
    """
    Mark a purchase as received.
    Adds stock for each item and creates stock movements.
    """
    with transaction.atomic():
        purchase = Purchase.objects.select_for_update().get(pk=purchase_id)

        if purchase.status != Purchase.Status.PENDING:
            raise ValueError(f"Purchase is already {purchase.status}")

        for item in purchase.items.select_related("medicine").all():
            # Add to stock (or update existing batch)
            stock, created = Stock.objects.get_or_create(
                medicine=item.medicine,
                batch_number=item.batch_number,
                defaults={
                    "quantity": item.quantity,
                    "expiry_date": item.expiry_date,
                    "purchase_price": item.unit_cost,
                },
            )
            if not created:
                stock.quantity += item.quantity
                stock.save(update_fields=["quantity", "updated_at"])

            # Update medicine cost price
            item.medicine.cost_price = item.unit_cost
            item.medicine.save(update_fields=["cost_price", "updated_at"])

            # Create stock movement
            StockMovement.objects.create(
                medicine=item.medicine,
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity=item.quantity,
                batch_number=item.batch_number,
                reference=f"Purchase #{purchase.pk}",
                notes=f"Received from {purchase.supplier.name}",
                created_by=user,
            )

        purchase.status = Purchase.Status.RECEIVED
        purchase.save(update_fields=["status", "updated_at"])

        return purchase


def cancel_purchase(purchase_id, user=None):
    """Cancel a pending purchase."""
    with transaction.atomic():
        purchase = Purchase.objects.get(pk=purchase_id)
        if purchase.status != Purchase.Status.PENDING:
            raise ValueError("Only pending purchases can be cancelled")
        purchase.status = Purchase.Status.CANCELLED
        purchase.save(update_fields=["status", "updated_at"])
        return purchase


# ─── Stock Dispensing ─────────────────────────────────────────────────

def dispense_stock(medicine_id, quantity, reference="", notes="", user=None):
    """
    Dispense stock (stock out).
    Uses FIFO: oldest batch first.
    Returns list of (batch_number, qty_dispensed) tuples.
    """
    with transaction.atomic():
        medicine = Medicine.objects.get(pk=medicine_id)
        batches = Stock.objects.select_for_update().filter(
            medicine=medicine, quantity__gt=0,
        ).order_by("expiry_date")

        total_available = sum(b.quantity for b in batches)
        if quantity > total_available:
            raise ValueError(
                f"Insufficient stock. Available: {total_available}, Requested: {quantity}"
            )

        remaining = quantity
        dispensed = []

        for batch in batches:
            if remaining <= 0:
                break
            dispense_qty = min(batch.quantity, remaining)
            batch.quantity -= dispense_qty
            batch.save(update_fields=["quantity", "updated_at"])
            remaining -= dispense_qty

            dispensed.append((batch.batch_number, dispense_qty))

            StockMovement.objects.create(
                medicine=medicine,
                movement_type=StockMovement.MovementType.DISPENSE,
                quantity=-dispense_qty,
                batch_number=batch.batch_number,
                reference=reference,
                notes=notes,
                created_by=user,
            )

        return dispensed


def adjust_stock(medicine_id, batch_number, new_quantity, reason, user=None):
    """Manually adjust stock for a batch."""
    with transaction.atomic():
        stock = Stock.objects.select_for_update().get(
            medicine_id=medicine_id, batch_number=batch_number,
        )
        old_qty = stock.quantity
        diff = new_quantity - old_qty
        stock.quantity = new_quantity
        stock.save(update_fields=["quantity", "updated_at"])

        StockMovement.objects.create(
            medicine_id=medicine_id,
            movement_type=StockMovement.MovementType.ADJUSTMENT,
            quantity=diff,
            batch_number=batch_number,
            reference=f"Adjustment: {old_qty} → {new_quantity}",
            notes=reason,
            created_by=user,
        )

        return stock


def mark_expired(medicine_id, batch_number, user=None):
    """Mark expired stock and create movement."""
    with transaction.atomic():
        stock = Stock.objects.select_for_update().get(
            medicine_id=medicine_id, batch_number=batch_number,
        )
        qty = stock.quantity
        stock.quantity = 0
        stock.save(update_fields=["quantity", "updated_at"])

        StockMovement.objects.create(
            medicine_id=medicine_id,
            movement_type=StockMovement.MovementType.EXPIRED,
            quantity=-qty,
            batch_number=batch_number,
            reference="Expired/Disposed",
            notes="Stock marked as expired",
            created_by=user,
        )

        return stock


# ─── Stock Movement History ───────────────────────────────────────────

def get_stock_movements(medicine_id=None):
    qs = StockMovement.objects.select_related("medicine", "created_by")
    if medicine_id:
        qs = qs.filter(medicine_id=medicine_id)
    return qs


# ─── Dashboard Stats ──────────────────────────────────────────────────

def get_dashboard_stats():
    total_medicines = Medicine.objects.filter(is_active=True).count()
    total_stock_value = Stock.objects.filter(quantity__gt=0).aggregate(
        total=Sum(F("quantity") * F("purchase_price"))
    )["total"] or 0
    low_stock_count = get_low_stock_medicines().count()
    expiring_count = get_expiring_medicines(30).count()
    expired_count = get_expired_stock().count()
    pending_purchases = Purchase.objects.filter(status=Purchase.Status.PENDING).count()

    return {
        "total_medicines": total_medicines,
        "total_stock_value": total_stock_value,
        "low_stock_count": low_stock_count,
        "expiring_count": expiring_count,
        "expired_count": expired_count,
        "pending_purchases": pending_purchases,
    }
