from django.views.generic import TemplateView


class WardsIndexView(TemplateView):
    template_name = "wards/list.html"
