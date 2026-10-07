from django.contrib.auth.mixins import UserPassesTestMixin

from .permissoes import eh_gerente


class GerenteRequiredMixin(UserPassesTestMixin):
    """Libera a página apenas para Gerentes; os demais recebem 403 (acesso negado)."""

    raise_exception = True

    def test_func(self):
        return eh_gerente(self.request.user)
