from django.urls import path
from . import views

app_name = "radiology"

urlpatterns = [
    path("", views.RadiologyQueueView.as_view(), name="radiology-list"),
    path("<int:visit_id>/", views.RadiologyVisitDetailView.as_view(), name="radiology-detail"),
    path("<int:visit_id>/draft/", views.RadiologySaveDraftView.as_view(), name="radiology-save-draft"),
    path("<int:visit_id>/result/<int:request_id>/", views.RadiologySubmitResultView.as_view(), name="radiology-submit-result"),
    path("<int:visit_id>/finalize/", views.RadiologyFinalizeResultsView.as_view(), name="radiology-finalize"),
    path("<int:visit_id>/complete/", views.RadiologyCompleteAllView.as_view(), name="radiology-complete-all"),
]
