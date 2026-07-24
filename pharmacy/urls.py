from django.urls import path
from . import views

app_name = "pharmacy"

urlpatterns = [
    path("", views.PharmacyQueueView.as_view(), name="pharmacy-list"),
    path("<int:visit_id>/", views.PharmacyDispenseView.as_view(), name="pharmacy-dispense"),
    path("dispense/<int:prescription_id>/", views.DispenseSingleView.as_view(), name="pharmacy-dispense-single"),
    path("<int:visit_id>/dispense-all/", views.DispenseAllView.as_view(), name="pharmacy-dispense-all"),
    path("<int:visit_id>/finish/", views.FinishVisitView.as_view(), name="pharmacy-finish-visit"),
    path("<int:visit_id>/history/", views.DispenseHistoryView.as_view(), name="pharmacy-history"),
]
