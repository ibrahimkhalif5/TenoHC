from django.urls import path
from . import views

app_name = "discharge"

urlpatterns = [
    path(
        "",
        views.DischargeSummaryListView.as_view(),
        name="discharge-summary-list",
    ),
    path(
        "admissions/",
        views.AdmissionForDischargeListView.as_view(),
        name="discharge-admission-list",
    ),
    path(
        "<int:admission_id>/create/",
        views.DischargeSummaryCreateView.as_view(),
        name="discharge-summary-create",
    ),
    path(
        "<int:summary_id>/",
        views.DischargeSummaryDetailView.as_view(),
        name="discharge-summary-detail",
    ),
    path(
        "<int:summary_id>/save/",
        views.DischargeSummarySaveView.as_view(),
        name="discharge-summary-save",
    ),
    path(
        "<int:summary_id>/finalize/",
        views.DischargeSummaryFinalizeView.as_view(),
        name="discharge-summary-finalize",
    ),
    path(
        "<int:summary_id>/pdf/",
        views.DischargeSummaryPDFView.as_view(),
        name="discharge-summary-pdf",
    ),
    path(
        "<int:summary_id>/print/",
        views.DischargeSummaryPrintView.as_view(),
        name="discharge-summary-print",
    ),
    path(
        "<int:summary_id>/medication/add/",
        views.DischargeMedicationAddView.as_view(),
        name="discharge-medication-add",
    ),
    path(
        "medication/<int:med_id>/remove/",
        views.DischargeMedicationRemoveView.as_view(),
        name="discharge-medication-remove",
    ),
]
