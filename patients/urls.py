from django.urls import path
from . import views

app_name = "patients"

urlpatterns = [
    path("", views.PatientListView.as_view(), name="patient-list"),
    path("register/", views.PatientRegisterView.as_view(), name="patient-register"),
    path("search/", views.PatientSearchAPIView.as_view(), name="patient-search-api"),
    path("<int:pk>/", views.PatientDetailView.as_view(), name="patient-detail"),
    path("<int:pk>/edit/", views.PatientUpdateView.as_view(), name="patient-edit"),
    path("<int:pk>/visit/", views.PatientCreateVisitView.as_view(), name="patient-create-visit"),
]
