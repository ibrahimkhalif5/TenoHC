from django.urls import path
from . import views

app_name = "cashier"

urlpatterns = [
    path("", views.CashierDashboardView.as_view(), name="cashier-list"),
    path("outstanding/", views.OutstandingView.as_view(), name="cashier-outstanding"),
    path("history/", views.PaymentHistoryView.as_view(), name="cashier-history"),
    path("invoice/<int:invoice_id>/pay/", views.PaymentCreateView.as_view(), name="cashier-pay"),
    path("receipt/<int:payment_id>/", views.ReceiptView.as_view(), name="cashier-receipt"),
    path("billing/", views.InvoiceListView.as_view(), name="billing-list"),
    path("billing/<int:invoice_id>/", views.InvoiceDetailView.as_view(), name="billing-detail"),
]
