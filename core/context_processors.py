def global_context(request):
    """Add global context variables to all templates."""
    return {
        "app_name": "THHIMS",
        "app_full_name": "TENOCARE HOSPITAL Information Management System",
    }
