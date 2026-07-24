from django import template

register = template.Library()


@register.inclusion_tag("triage/partials/status_badge.html", takes_context=True)
def visit_status_badge(context, visit, show_link=True):
    """Render a clickable status badge for a visit."""
    badge_classes = {
        "WAITING_TRIAGE": "bg-secondary",
        "IN_TRIAGE": "bg-info",
        "WAITING_DOCTOR": "bg-primary",
        "IN_CONSULTATION": "bg-warning text-dark",
        "WAITING_LAB": "bg-info",
        "WAITING_XRAY": "bg-info",
        "WAITING_ULTRASOUND": "bg-info",
        "WAITING_DOCTOR_REVIEW": "bg-primary",
        "WAITING_PHARMACY": "bg-success",
        "ADMISSION_IN_PROGRESS": "bg-dark",
        "DISCHARGED": "bg-success",
        "COMPLETED": "bg-success",
        "CANCELLED": "bg-danger",
    }
    return {
        "visit": visit,
        "show_link": show_link,
        "badge_class": badge_classes.get(visit.status, "bg-secondary"),
    }
