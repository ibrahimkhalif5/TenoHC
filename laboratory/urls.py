from django.urls import path
from . import views

app_name = "laboratory"

urlpatterns = [
    path("", views.LabQueueView.as_view(), name="lab-list"),
    path("<int:visit_id>/", views.LabVisitDetailView.as_view(), name="lab-detail"),
    path("<int:visit_id>/draft/", views.LabSaveDraftView.as_view(), name="lab-save-draft"),
    path("<int:visit_id>/finalize/", views.LabFinalizeResultsView.as_view(), name="lab-finalize"),
    path("<int:visit_id>/complete/", views.LabCompleteAllView.as_view(), name="lab-complete-all"),
    path("<int:visit_id>/report/", views.LabReportPDFView.as_view(), name="lab-report-pdf"),
    path("<int:visit_id>/print/", views.LabReportPrintView.as_view(), name="lab-report-print"),
]
