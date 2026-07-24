from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View


class BillingIndexView(LoginRequiredMixin, View):
    """Redirect to cashier invoice list."""

    def get(self, request):
        return redirect("cashier:billing-list")
