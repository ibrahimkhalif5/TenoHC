from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView


class DashboardRedirectView(TemplateView):
    template_name = "accounts/dashboard.html"
