from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction

from core.models import TimeStampedModel
from core.validators import validar_telefone

from .permissoes import GRUPO_GERENTE, GRUPO_VENDEDOR, obter_grupos


class Perfil(TimeStampedModel):
    """Dados extras do usuário e o papel que define suas regras de acesso."""

    class Papel(models.TextChoices):
        GERENTE = "gerente", "Gerente"
        VENDEDOR = "vendedor", "Vendedor"

    GRUPO_DO_PAPEL = {
        Papel.GERENTE: GRUPO_GERENTE,
        Papel.VENDEDOR: GRUPO_VENDEDOR,
    }

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    papel = models.CharField(
        "papel", max_length=20, choices=Papel.choices, default=Papel.VENDEDOR,
        help_text=(
            "Vendedor: vê apenas as próprias vendas. "
            "Gerente: vê as vendas de todos, os dashboards gerenciais e acessa o painel /admin."
        ),
    )
    telefone = models.CharField("telefone", max_length=15, blank=True, validators=[validar_telefone])

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfis"

    def __str__(self):
        return f"{self.usuario} ({self.get_papel_display()})"

    @classmethod
    def papel_inicial(cls, usuario):
        return cls.Papel.GERENTE if usuario.is_superuser else cls.Papel.VENDEDOR

    @property
    def eh_gerente(self):
        return self.papel == self.Papel.GERENTE or self.usuario.is_superuser

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.aplicar_regras()

    def aplicar_regras(self):
        """Coloca o usuário apenas no grupo do seu papel e ajusta o acesso ao /admin."""
        grupos = obter_grupos()
        usuario = self.usuario
        usuario.groups.remove(*grupos.values())
        usuario.groups.add(grupos[self.GRUPO_DO_PAPEL[self.papel]])

        acesso_admin = self.papel == self.Papel.GERENTE or usuario.is_superuser
        if usuario.is_staff != acesso_admin:
            get_user_model().objects.filter(pk=usuario.pk).update(is_staff=acesso_admin)
            usuario.is_staff = acesso_admin
