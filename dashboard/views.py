from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render

from . import services


class DashboardIndexView(LoginRequiredMixin, View):
    """Role-based dashboard with aggregated stats and charts."""

    def get(self, request):
        context = services.get_dashboard_context(request.user)
        return render(request, "dashboard/index.html", context)
