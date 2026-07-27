from django.urls import path
from . import views

app_name = "consultation"

urlpatterns = [
    path("", views.DoctorQueueView.as_view(), name="consultation-list"),
    path("start/<int:visit_id>/", views.StartConsultationView.as_view(), name="start-consultation"),
    path("<int:consultation_id>/conduct/", views.ConductConsultationView.as_view(), name="conduct-consultation"),
    path("<int:consultation_id>/print/", views.ConsultationPrintView.as_view(), name="consultation-print"),
    path("<int:consultation_id>/general-report/", views.GeneralReportView.as_view(), name="general-report"),
    path("<int:consultation_id>/", views.ConsultationDetailView.as_view(), name="consultation-detail"),
    path("visit/<int:visit_id>/history/", views.ConsultationHistoryView.as_view(), name="visit-history"),
]
