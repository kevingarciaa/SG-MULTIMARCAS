from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum

from core.models import TimeStampedModel
from core.validators import somente_digitos, validar_cpf, validar_telefone


class ClienteQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)


class Cliente(TimeStampedModel):
    nome = models.CharField("nome completo", max_length=150)
    cpf = models.CharField(
        "CPF", max_length=14, unique=True, blank=True, null=True, validators=[validar_cpf],
        help_text="Com ou sem pontuação. É salvo somente com números.",
    )
    telefone = models.CharField("telefone", max_length=15, validators=[validar_telefone])
    email = models.EmailField("e-mail", blank=True)
    data_nascimento = models.DateField("data de nascimento", blank=True, null=True)
    endereco = models.CharField("endereço", max_length=200, blank=True)
    bairro = models.CharField("bairro", max_length=100, blank=True)
    cidade = models.CharField("cidade", max_length=100, blank=True)
    observacoes = models.TextField("observações", blank=True)
    ativo = models.BooleanField("ativo", default=True)
    cadastrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="clientes_cadastrados",
        blank=True, null=True, editable=False,
    )

    objects = ClienteQuerySet.as_manager()

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        self.cpf = somente_digitos(self.cpf) or None
        self.telefone = somente_digitos(self.telefone)
        super().save(*args, **kwargs)

    @property
    def cpf_formatado(self):
        if not self.cpf:
            return ""
        c = self.cpf
        return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"

    @property
    def telefone_formatado(self):
        t = self.telefone
        if len(t) == 11:
            return f"({t[:2]}) {t[2:7]}-{t[7:]}"
        if len(t) == 10:
            return f"({t[:2]}) {t[2:6]}-{t[6:]}"
        return t

    @property
    def total_em_aberto(self):
        """Soma do que o cliente ainda deve em promissórias abertas (inclui vencidas)."""
        totais = self.promissorias.em_aberto().aggregate(valor=Sum("valor"), pago=Sum("valor_pago"))
        return (totais["valor"] or Decimal("0")) - (totais["pago"] or Decimal("0"))

    @property
    def possui_vencidas(self):
        return self.promissorias.vencidas().exists()

    @property
    def situacao_financeira(self):
        if self.possui_vencidas:
            return "Inadimplente"
        if self.total_em_aberto > 0:
            return "Com débitos em dia"
        return "Em dia"
