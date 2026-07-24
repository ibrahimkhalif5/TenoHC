from django.urls import path
from . import views

app_name = "triage"

urlpatterns = [
    path("", views.TriageQueueView.as_view(), name="triage-list"),
    path("<int:visit_id>/assess/", views.TriageAssessView.as_view(), name="triage-assess"),
]
