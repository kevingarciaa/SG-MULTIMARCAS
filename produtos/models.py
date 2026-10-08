from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction

from core.models import TimeStampedModel


class ProdutoQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)


class Produto(TimeStampedModel):
    CAMPOS_HISTORICO = {
        "nome": "Nome",
        "marca": "Marca",
        "codigo": "Código",
        "preco": "Preço",
        "estoque": "Estoque",
        "descricao": "Descrição",
        "ativo": "Ativo",
    }

    nome = models.CharField("nome", max_length=150)
    codigo = models.CharField(
        "código", max_length=50, unique=True, blank=True, null=True,
        help_text="Código interno ou de barras (opcional).",
    )
    marca = models.CharField("marca", max_length=100, blank=True)
    descricao = models.TextField("descrição", blank=True)
    preco = models.DecimalField(
        "preço de venda", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    estoque = models.PositiveIntegerField("quantidade em estoque", default=0)
    ativo = models.BooleanField("ativo", default=True)

    objects = ProdutoQuerySet.as_manager()

    class Meta:
        verbose_name = "produto"
        verbose_name_plural = "produtos"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.marca})" if self.marca else self.nome

    def save(self, *args, usuario=None, **kwargs):
        self.codigo = (self.codigo or "").strip() or None
        novo = self.pk is None
        anteriores = {} if novo else (
            Produto.objects.filter(pk=self.pk).values(*self.CAMPOS_HISTORICO).first() or {}
        )

        with transaction.atomic():
            super().save(*args, **kwargs)
            if novo:
                self.registrar_historico("Cadastro", "Produto cadastrado.", usuario)
            else:
                alteracoes = [
                    f"{rotulo}: {self._formatar(anteriores.get(campo))} → {self._formatar(getattr(self, campo))}"
                    for campo, rotulo in self.CAMPOS_HISTORICO.items()
                    if anteriores.get(campo) != getattr(self, campo)
                ]
                if alteracoes:
                    self.registrar_historico("Alteração", "\n".join(alteracoes), usuario)

    def registrar_historico(self, acao, descricao="", usuario=None):
        return self.historico.create(acao=acao, descricao=descricao, usuario=usuario)

    @staticmethod
    def _formatar(valor):
        if valor is None or valor == "":
            return "(vazio)"
        if isinstance(valor, bool):
            return "Sim" if valor else "Não"
        if isinstance(valor, Decimal):
            return f"R$ {valor:.2f}".replace(".", ",")
        return f"'{valor}'"


class HistoricoProduto(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="historico")
    data = models.DateTimeField("data", auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
    )
    acao = models.CharField("ação", max_length=50)
    descricao = models.TextField("descrição", blank=True)

    class Meta:
        verbose_name = "histórico do produto"
        verbose_name_plural = "histórico dos produtos"
        ordering = ["-data", "-pk"]

    def __str__(self):
        return f"{self.data:%d/%m/%Y %H:%M} - {self.acao}"
