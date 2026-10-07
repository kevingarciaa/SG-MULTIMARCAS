from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone

from core.models import TimeStampedModel


class VendaQuerySet(models.QuerySet):
    def concluidas(self):
        return self.filter(status=Venda.Status.CONCLUIDA)

    def visiveis_para(self, usuario):
        """Gerente vê todas as vendas; vendedor vê somente as que ele registrou."""
        from accounts.permissoes import eh_gerente

        return self if eh_gerente(usuario) else self.filter(vendedor=usuario)


class Venda(TimeStampedModel):
    class FormaPagamento(models.TextChoices):
        DINHEIRO = "dinheiro", "Dinheiro"
        PIX = "pix", "Pix"
        DEBITO = "debito", "Cartão de débito"
        CREDITO = "credito", "Cartão de crédito"
        PROMISSORIA = "promissoria", "Promissória"

    class Status(models.TextChoices):
        CONCLUIDA = "concluida", "Concluída"
        CANCELADA = "cancelada", "Cancelada"

    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.PROTECT, related_name="vendas",
        blank=True, null=True, help_text="Obrigatório para vendas em promissória.",
    )
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="vendas",
        blank=True, null=True,
    )
    data_venda = models.DateTimeField("data da venda", default=timezone.now)
    forma_pagamento = models.CharField("forma de pagamento", max_length=20, choices=FormaPagamento.choices)
    desconto = models.DecimalField(
        "desconto", max_digits=10, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    valor_total = models.DecimalField("valor total", max_digits=12, decimal_places=2, default=Decimal("0"), editable=False)
    status = models.CharField("situação", max_length=20, choices=Status.choices, default=Status.CONCLUIDA)
    observacoes = models.TextField("observações", blank=True)

    objects = VendaQuerySet.as_manager()

    class Meta:
        verbose_name = "venda"
        verbose_name_plural = "vendas"
        ordering = ["-data_venda"]

    def __str__(self):
        return f"Venda #{self.pk} - {self.cliente or 'Consumidor'}"

    def clean(self):
        if self.forma_pagamento == self.FormaPagamento.PROMISSORIA and not self.cliente_id:
            raise ValidationError({"cliente": "Informe o cliente para vendas em promissória."})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.recalcular_total()

    @property
    def subtotal(self):
        expr = ExpressionWrapper(F("quantidade") * F("preco_unitario"), output_field=DecimalField())
        return self.itens.aggregate(total=Sum(expr))["total"] or Decimal("0")

    def recalcular_total(self):
        """Atualiza valor_total a partir dos itens (subtotal - desconto)."""
        self.valor_total = max(self.subtotal - self.desconto, Decimal("0"))
        Venda.objects.filter(pk=self.pk).update(valor_total=self.valor_total)


class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey("produtos.Produto", on_delete=models.PROTECT, related_name="itens_venda")
    quantidade = models.PositiveIntegerField("quantidade", validators=[MinValueValidator(1)])
    preco_unitario = models.DecimalField(
        "preço unitário", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))], blank=True,
        help_text="Preço no momento da venda. Se ficar vazio, usa o preço atual do produto.",
    )

    class Meta:
        verbose_name = "item da venda"
        verbose_name_plural = "itens da venda"

    def __str__(self):
        return f"{self.quantidade}x {self.produto}"

    @property
    def subtotal(self):
        return (self.quantidade or 0) * (self.preco_unitario or Decimal("0"))

    def save(self, *args, **kwargs):
        if self.preco_unitario is None and self.produto_id:
            self.preco_unitario = self.produto.preco
        super().save(*args, **kwargs)
        self.venda.recalcular_total()

    def delete(self, *args, **kwargs):
        venda = self.venda
        resultado = super().delete(*args, **kwargs)
        venda.recalcular_total()
        return resultado
