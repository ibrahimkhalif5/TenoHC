from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.views.static import serve as static_serve

admin.site.site_header = "TCHIMS Administration"
admin.site.site_title = "TCHIMS Admin"
admin.site.index_title = "Hospital Management"

urlpatterns = [
    path("", RedirectView.as_view(url="/dashboard/", permanent=True)),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("core.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("patients/", include("patients.urls")),
    path("triage/", include("triage.urls")),
    path("consultation/", include("consultation.urls")),
    path("laboratory/", include("laboratory.urls")),
    path("radiology/", include("radiology.urls")),
    path("pharmacy/", include("pharmacy.urls")),
    path("admission/", include("admission.urls")),
    path("discharge/", include("discharge.urls")),
    path("wards/", include("wards.urls")),
    path("nursing/", include("nursing.urls")),
    path("billing/", include("billing.urls")),
    path("cashier/", include("cashier.urls")),
    path("inventory/", include("inventory.urls")),
    path("reports/", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Serve media files in production (e.g., PythonAnywhere) via Django
    # NOTE: For high-traffic sites, configure your web server to serve /media/ directly
    urlpatterns += [
        path(
            "media/<path:path>",
            static_serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
