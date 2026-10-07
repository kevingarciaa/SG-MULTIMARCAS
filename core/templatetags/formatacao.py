from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def moeda(valor):
    """Formata um número como Real: 1234.5 -> 'R$ 1.234,50'."""
    try:
        valor = Decimal(valor or 0)
    except (InvalidOperation, TypeError, ValueError):
        return valor
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


@register.filter
def nome_usuario(usuario):
    """Nome completo do usuário, ou o login quando o nome não foi preenchido."""
    if not usuario:
        return "Sem vendedor"
    return usuario.get_full_name() or usuario.username


@register.filter
def percentual(valor, casas=1):
    """Formata um número como porcentagem: 12.345 -> '12,3%'."""
    try:
        return f"{float(valor or 0):.{int(casas)}f}%".replace(".", ",")
    except (TypeError, ValueError):
        return valor
