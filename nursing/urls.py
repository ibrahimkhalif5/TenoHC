from django.urls import path
from . import views

app_name = "nursing"

urlpatterns = [
    path("", views.PatientListView.as_view(), name="nursing-list"),
    path("<int:admission_id>/", views.PatientDetailView.as_view(), name="nursing-detail"),
    path("<int:admission_id>/note/", views.AddNursingNoteView.as_view(), name="nursing-add-note"),
    path("<int:admission_id>/vitals/", views.AddDailyVitalsView.as_view(), name="nursing-add-vitals"),
    path("<int:admission_id>/treatment/", views.AddTreatmentView.as_view(), name="nursing-add-treatment"),
]
