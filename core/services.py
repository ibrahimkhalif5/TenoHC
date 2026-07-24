import logging

from .models import AuditLog

audit_logger = logging.getLogger("audit")


def log_action(user, action, model_name, object_id=None, object_repr="", description="", request=None):
    """Log an action to the audit trail."""
    ip_address = None
    if request:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            ip_address = x_forwarded.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR")

    audit_log = AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        object_repr=str(object_repr)[:200],
        description=description,
        ip_address=ip_address,
    )
    audit_logger.info(f"{user} {action} {model_name}#{object_id}: {description}")
    return audit_log
