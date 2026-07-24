from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="inventory-dashboard"),
    path("medicines/", views.MedicineListView.as_view(), name="inventory-medicines"),
    path("medicines/create/", views.MedicineCreateView.as_view(), name="inventory-medicine-create"),
    path("medicines/<int:medicine_id>/", views.MedicineDetailView.as_view(), name="inventory-medicine-detail"),
    path("medicines/<int:medicine_id>/edit/", views.MedicineEditView.as_view(), name="inventory-medicine-edit"),
    path("medicines/<int:medicine_id>/delete/", views.MedicineDeleteView.as_view(), name="inventory-medicine-delete"),
    path("medicines/<int:medicine_id>/dispense/", views.DispenseView.as_view(), name="inventory-dispense"),
    path("suppliers/", views.SupplierListView.as_view(), name="inventory-suppliers"),
    path("suppliers/create/", views.SupplierCreateView.as_view(), name="inventory-supplier-create"),
    path("purchases/", views.PurchaseListView.as_view(), name="inventory-purchases"),
    path("purchases/create/", views.PurchaseCreateView.as_view(), name="inventory-purchase-create"),
    path("purchases/<int:purchase_id>/", views.PurchaseDetailView.as_view(), name="inventory-purchase-detail"),
    path("purchases/<int:purchase_id>/receive/", views.PurchaseReceiveView.as_view(), name="inventory-purchase-receive"),
    path("purchases/<int:purchase_id>/cancel/", views.PurchaseCancelView.as_view(), name="inventory-purchase-cancel"),
    path("stock/", views.StockListView.as_view(), name="inventory-stock"),
    path("stock/<int:stock_id>/adjust/", views.StockAdjustView.as_view(), name="inventory-stock-adjust"),
    path("low-stock/", views.LowStockView.as_view(), name="inventory-low-stock"),
    path("expiring/", views.ExpiringView.as_view(), name="inventory-expiring"),
    path("movements/", views.MovementHistoryView.as_view(), name="inventory-movements"),
    path("api/medicines/", views.MedicineSearchAPIView.as_view(), name="inventory-api-medicines"),
    path("api/medicine-resolve/", views.MedicineResolveAPIView.as_view(), name="inventory-api-medicine-resolve"),
]
