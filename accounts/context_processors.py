from .permissoes import eh_gerente


def papel(request):
    """Disponibiliza {{ eh_gerente }} em todos os templates (menu, dashboards etc.)."""
    return {"eh_gerente": eh_gerente(request.user)}
