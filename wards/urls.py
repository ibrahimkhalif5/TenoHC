from django.urls import path
from . import views

app_name = "wards"

urlpatterns = [
    path("", views.WardsIndexView.as_view(), name="ward-list"),
]
