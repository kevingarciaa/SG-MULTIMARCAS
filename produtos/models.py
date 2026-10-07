from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from core.models import TimeStampedModel


class ProdutoQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)


class Produto(TimeStampedModel):
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

    def save(self, *args, **kwargs):
        self.codigo = (self.codigo or "").strip() or None
        super().save(*args, **kwargs)
