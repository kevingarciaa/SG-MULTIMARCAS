from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Max, Sum
from django.utils import timezone

from core.models import TimeStampedModel
from core.templatetags.formatacao import moeda


class PromissoriaQuerySet(models.QuerySet):
    def em_aberto(self):
        """Abertas, incluindo as vencidas (ainda não pagas nem canceladas)."""
        return self.filter(status=Promissoria.Status.ABERTA)

    def vencidas(self):
        return self.em_aberto().filter(data_vencimento__lt=timezone.localdate())

    def a_vencer(self, dias=None):
        """Abertas que vencem entre hoje e os próximos `dias` dias."""
        dias = settings.PROMISSORIA_DIAS_ALERTA if dias is None else dias
        hoje = timezone.localdate()
        return self.em_aberto().filter(data_vencimento__range=(hoje, hoje + timedelta(days=dias)))

    def pagas(self):
        return self.filter(status=Promissoria.Status.PAGA)

    def canceladas(self):
        return self.filter(status=Promissoria.Status.CANCELADA)


class Promissoria(TimeStampedModel):
    class Status(models.TextChoices):
        ABERTA = "aberta", "Aberta"
        PAGA = "paga", "Paga"
        CANCELADA = "cancelada", "Cancelada"

    # "Vencida" não é gravada no banco: é calculada a partir da data de vencimento.
    # Assim a promissória fica vencida automaticamente, sem rotina agendada.
    SITUACAO_VENCIDA = "vencida"

    CAMPOS_HISTORICO = {
        "valor": "Valor",
        "data_vencimento": "Vencimento",
        "status": "Status",
        "observacoes": "Observações",
    }

    numero = models.CharField("número", max_length=20, unique=True, editable=False, blank=True)
    cliente = models.ForeignKey("clientes.Cliente", on_delete=models.PROTECT, related_name="promissorias")
    venda = models.ForeignKey(
        "vendas.Venda", on_delete=models.PROTECT, related_name="promissorias", blank=True, null=True,
    )
    valor = models.DecimalField(
        "valor", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))],
    )
    data_emissao = models.DateField("data de emissão", default=timezone.localdate)
    data_vencimento = models.DateField("data de vencimento")
    status = models.CharField("status", max_length=20, choices=Status.choices, default=Status.ABERTA)
    valor_pago = models.DecimalField("valor pago", max_digits=10, decimal_places=2, default=Decimal("0"), editable=False)
    data_pagamento = models.DateField("data do pagamento", blank=True, null=True, editable=False)
    observacoes = models.TextField("observações", blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="promissorias_criadas",
        blank=True, null=True, editable=False,
    )

    objects = PromissoriaQuerySet.as_manager()

    class Meta:
        verbose_name = "promissória"
        verbose_name_plural = "promissórias"
        ordering = ["data_vencimento", "pk"]
        indexes = [models.Index(fields=["status", "data_vencimento"])]

    def __str__(self):
        return f"Promissória {self.numero or '(nova)'} - {self.cliente}"

    # ---------- Valores calculados ----------

    @property
    def valor_em_aberto(self):
        if self.status == self.Status.CANCELADA:
            return Decimal("0")
        return max((self.valor or Decimal("0")) - self.valor_pago, Decimal("0"))

    @property
    def esta_vencida(self):
        return self.status == self.Status.ABERTA and self.data_vencimento < timezone.localdate()

    @property
    def dias_atraso(self):
        if not self.esta_vencida:
            return 0
        return (timezone.localdate() - self.data_vencimento).days

    @property
    def dias_para_vencer(self):
        return (self.data_vencimento - timezone.localdate()).days

    @property
    def situacao(self):
        return self.SITUACAO_VENCIDA if self.esta_vencida else self.status

    @property
    def situacao_display(self):
        return "Vencida" if self.esta_vencida else self.get_status_display()

    @property
    def situacao_cor(self):
        """Cor do Bootstrap usada nos badges da interface."""
        return {
            self.SITUACAO_VENCIDA: "danger",
            self.Status.ABERTA: "warning",
            self.Status.PAGA: "success",
            self.Status.CANCELADA: "secondary",
        }[self.situacao]

    # ---------- Validação ----------

    def clean(self):
        erros = {}
        if self.data_vencimento and self.data_emissao and self.data_vencimento < self.data_emissao:
            erros["data_vencimento"] = "O vencimento não pode ser anterior à emissão."
        if self.venda_id and self.cliente_id and self.venda.cliente_id != self.cliente_id:
            erros["venda"] = "A venda selecionada pertence a outro cliente."
        if self.pk and self.valor is not None and self.valor < self.valor_pago:
            erros["valor"] = "O valor não pode ser menor que o total já pago."
        if erros:
            raise ValidationError(erros)

    # ---------- Persistência e histórico ----------

    def save(self, *args, usuario=None, **kwargs):
        novo = self.pk is None
        anteriores = {} if novo else (
            Promissoria.objects.filter(pk=self.pk).values(*self.CAMPOS_HISTORICO).first() or {}
        )
        if novo and usuario and not self.criado_por_id:
            self.criado_por = usuario

        with transaction.atomic():
            super().save(*args, **kwargs)
            if not self.numero:
                self.numero = f"{self.data_emissao:%Y}-{self.pk:05d}"
                Promissoria.objects.filter(pk=self.pk).update(numero=self.numero)

            if novo:
                self.registrar_historico("Criação", f"Promissória criada no valor de R$ {self.valor}.", usuario)
            else:
                alteracoes = [
                    f"{rotulo}: '{anteriores.get(campo)}' → '{getattr(self, campo)}'"
                    for campo, rotulo in self.CAMPOS_HISTORICO.items()
                    if anteriores.get(campo) != getattr(self, campo)
                ]
                if alteracoes:
                    self.registrar_historico("Alteração", "\n".join(alteracoes), usuario)

    def registrar_historico(self, acao, descricao="", usuario=None):
        return self.historico.create(acao=acao, descricao=descricao, usuario=usuario)

    def atualizar_pagamentos(self, usuario=None):
        """Recalcula valor pago e status a partir dos pagamentos válidos."""
        if self.status == self.Status.CANCELADA:
            return
        totais = self.pagamentos.filter(cancelado=False).aggregate(
            total=Sum("valor"), ultima_data=Max("data_pagamento")
        )
        self.valor_pago = totais["total"] or Decimal("0")
        if self.valor_pago >= self.valor:
            self.status = self.Status.PAGA
            self.data_pagamento = totais["ultima_data"]
        else:
            self.status = self.Status.ABERTA
            self.data_pagamento = None
        self.save(usuario=usuario)

    def cancelar(self, motivo, usuario=None):
        if self.status == self.Status.PAGA:
            raise ValidationError("Não é possível cancelar uma promissória já paga.")
        self.status = self.Status.CANCELADA
        self.save(usuario=usuario)
        self.registrar_historico("Cancelamento", motivo, usuario)


class Pagamento(TimeStampedModel):
    class Forma(models.TextChoices):
        DINHEIRO = "dinheiro", "Dinheiro"
        PIX = "pix", "Pix"
        DEBITO = "debito", "Cartão de débito"
        CREDITO = "credito", "Cartão de crédito"

    promissoria = models.ForeignKey(Promissoria, on_delete=models.PROTECT, related_name="pagamentos")
    valor = models.DecimalField(
        "valor pago", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))],
    )
    data_pagamento = models.DateField("data do pagamento", default=timezone.localdate)
    forma_pagamento = models.CharField("forma de pagamento", max_length=20, choices=Forma.choices)
    recebido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pagamentos_recebidos",
        blank=True, null=True,
    )
    observacoes = models.CharField("observações", max_length=255, blank=True)
    cancelado = models.BooleanField("cancelado", default=False)
    motivo_cancelamento = models.CharField("motivo do cancelamento", max_length=255, blank=True)

    class Meta:
        verbose_name = "pagamento"
        verbose_name_plural = "pagamentos"
        ordering = ["-data_pagamento", "-pk"]

    def __str__(self):
        return f"R$ {self.valor} em {self.data_pagamento:%d/%m/%Y}"

    def clean(self):
        if not self.promissoria_id or self.pk:
            return
        if self.promissoria.status == Promissoria.Status.CANCELADA:
            raise ValidationError("Não é possível registrar pagamento em promissória cancelada.")
        if self.valor and self.valor > self.promissoria.valor_em_aberto:
            raise ValidationError(
                {"valor": f"O valor excede o saldo em aberto ({moeda(self.promissoria.valor_em_aberto)})."}
            )

    def save(self, *args, **kwargs):
        novo = self.pk is None
        with transaction.atomic():
            super().save(*args, **kwargs)
            if novo:
                self.promissoria.registrar_historico(
                    "Pagamento", f"Pagamento de R$ {self.valor} ({self.get_forma_pagamento_display()}).",
                    self.recebido_por,
                )
            self.promissoria.atualizar_pagamentos(usuario=self.recebido_por)

    def cancelar(self, motivo, usuario=None):
        self.cancelado = True
        self.motivo_cancelamento = motivo
        with transaction.atomic():
            super().save(update_fields=["cancelado", "motivo_cancelamento", "atualizado_em"])
            self.promissoria.registrar_historico("Pagamento cancelado", f"R$ {self.valor}: {motivo}", usuario)
            self.promissoria.atualizar_pagamentos(usuario=usuario)


class HistoricoPromissoria(models.Model):
    promissoria = models.ForeignKey(Promissoria, on_delete=models.CASCADE, related_name="historico")
    data = models.DateTimeField("data", auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True,
    )
    acao = models.CharField("ação", max_length=50)
    descricao = models.TextField("descrição", blank=True)

    class Meta:
        verbose_name = "histórico da promissória"
        verbose_name_plural = "histórico das promissórias"
        ordering = ["-data", "-pk"]

    def __str__(self):
        return f"{self.data:%d/%m/%Y %H:%M} - {self.acao}"
