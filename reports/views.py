from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from .forms import ReportDateForm
from . import services


class ReportsIndexView(LoginRequiredMixin, View):
    template_name = "reports/list.html"

    def get(self, request):
        report_type = request.GET.get("type", "financial")
        start_date = request.GET.get("start_date", "")
        end_date = request.GET.get("end_date", "")

        form = ReportDateForm(initial={
            "report_type": report_type,
            "start_date": start_date,
            "end_date": end_date,
        })

        data = services.get_report(report_type, start_date or None, end_date or None)

        return render(request, self.template_name, {
            "form": form,
            "report_type": report_type,
            "data": data,
        })
