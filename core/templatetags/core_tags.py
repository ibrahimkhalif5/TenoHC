from django import template
from django.urls import reverse, NoReverseMatch

register = template.Library()


@register.simple_tag(takes_context=True)
def active(context, url_name, *args, **kwargs):
    """Return 'active' CSS class if the current path matches the given URL."""
    try:
        url = reverse(url_name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        url = url_name
    request = context.get("request")
    if request and (request.path == url or request.path.startswith(url + "/")):
        return "active"
    return ""


@register.filter
def add_class(field, css_class):
    """Add a CSS class to a form field widget."""
    return field.as_widget(attrs={"class": css_class})


@register.simple_tag
def get_current_year():
    from django.utils import timezone
    return timezone.now().year
