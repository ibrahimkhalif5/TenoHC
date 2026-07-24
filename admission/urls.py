from django.urls import path
from . import views

app_name = "admission"

urlpatterns = [
    path("", views.AdmissionQueueView.as_view(), name="admission-list"),
    path("<int:visit_id>/admit/", views.AdmissionCreateView.as_view(), name="admission-create"),
    path("<int:admission_id>/discharge/", views.AdmissionDischargeView.as_view(), name="admission-discharge"),
    path("wards/", views.WardManageView.as_view(), name="ward-manage"),
    path("wards/create/", views.WardCreateView.as_view(), name="ward-create"),
    path("wards/<int:ward_id>/edit/", views.WardEditView.as_view(), name="ward-edit"),
    path("rooms/create/", views.RoomCreateView.as_view(), name="room-create"),
    path("beds/create/", views.BedCreateView.as_view(), name="bed-create"),
    path("api/rooms/", views.RoomListAPIView.as_view(), name="api-rooms"),
    path("api/beds/", views.BedListAPIView.as_view(), name="api-beds"),
]
