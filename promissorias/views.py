from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Max, Min, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView

from clientes.models import Cliente
from core.templatetags.formatacao import moeda
from vendas.models import ItemVenda, Venda

from .forms import PagamentoForm
from .models import Pagamento, Promissoria

ZERO = Value(Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=2))


class PagamentosListView(PermissionRequiredMixin, ListView):
    """Busca de clientes com o quanto cada um deve; quem tem promissória vencida aparece primeiro."""

    permission_required = "promissorias.view_promissoria"
    template_name = "pagamentos/lista.html"
    context_object_name = "clientes"
    paginate_by = 20

    def get_queryset(self):
        hoje = timezone.localdate()
        aberta = Q(promissorias__status=Promissoria.Status.ABERTA)
        clientes = Cliente.objects.annotate(
            em_aberto=Coalesce(Sum(F("promissorias__valor") - F("promissorias__valor_pago"), filter=aberta), ZERO),
            vencidas=Count("promissorias", filter=aberta & Q(promissorias__data_vencimento__lt=hoje)),
            proximo_vencimento=Min("promissorias__data_vencimento", filter=aberta),
        )
        busca = self.request.GET.get("q", "").strip()
        if busca:
            digitos = "".join(c for c in busca if c.isdigit())
            filtro = Q(nome__icontains=busca)
            if digitos:
                filtro |= Q(cpf__contains=digitos) | Q(telefone__contains=digitos)
            clientes = clientes.filter(filtro)
        else:
            clientes = clientes.ativos()
        if not self.request.GET.get("todos"):
            clientes = clientes.filter(em_aberto__gt=0)
        return clientes.order_by("-vencidas", F("proximo_vencimento").asc(nulls_last=True), "nome")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        abertas = Promissoria.objects.em_aberto()
        saldo = ExpressionWrapper(F("valor") - F("valor_pago"), output_field=DecimalField())
        context["totais"] = {
            "em_aberto": abertas.aggregate(v=Sum(saldo))["v"] or Decimal("0"),
            "vencido": abertas.vencidas().aggregate(v=Sum(saldo))["v"] or Decimal("0"),
            "clientes": abertas.values("cliente").distinct().count(),
        }
        return context


class RegistrarPagamentoView(PermissionRequiredMixin, CreateView):
    permission_required = "promissorias.add_pagamento"
    form_class = PagamentoForm
    template_name = "pagamentos/registrar.html"

    def dispatch(self, request, *args, **kwargs):
        self.cliente = get_object_or_404(Cliente, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["cliente"] = self.cliente
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        promissoria = (
            self.cliente.promissorias.em_aberto().filter(pk=self.request.GET.get("promissoria") or 0).first()
            or self.cliente.promissorias.em_aberto().first()
        )
        if promissoria:
            initial["promissoria"] = promissoria
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cliente"] = self.cliente
        return context

    def form_valid(self, form):
        form.instance.recebido_por = self.request.user
        resposta = super().form_valid(form)
        promissoria = self.object.promissoria
        mensagem = f"Pagamento de {moeda(self.object.valor)} registrado na promissória {promissoria.numero}."
        if promissoria.status == Promissoria.Status.PAGA:
            mensagem += " A promissória foi quitada."
        messages.success(self.request, mensagem)
        return resposta

    def get_success_url(self):
        return reverse("pagamentos:cliente", args=[self.cliente.pk])


class ComprasClienteView(PermissionRequiredMixin, DetailView):
    """Todas as compras do cliente, item por item."""

    permission_required = "promissorias.view_promissoria"
    model = Cliente
    template_name = "pagamentos/compras.html"
    context_object_name = "cliente"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendas = Venda.objects.visiveis_para(self.request.user).filter(cliente=self.object)
        totais = vendas.concluidas().aggregate(quantidade=Count("id"), valor=Sum("valor_total"))
        context.update({
            "vendas": vendas.select_related("vendedor").prefetch_related("itens__produto"),
            "total_compras": totais["quantidade"],
            "total_valor": totais["valor"] or Decimal("0"),
        })
        return context


class HistoricoClienteView(PermissionRequiredMixin, DetailView):
    """Linha do tempo do cliente: compras, promissórias, pagamentos, quitações e cancelamentos."""

    permission_required = "promissorias.view_promissoria"
    model = Cliente
    template_name = "pagamentos/historico.html"
    context_object_name = "cliente"
    FILTROS = {"compras": "Compras", "promissorias": "Promissórias", "pagamentos": "Pagamentos"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtro = self.request.GET.get("tipo", "")
        filtro = filtro if filtro in self.FILTROS else ""
        eventos = []
        if filtro in ("", "compras"):
            eventos += self.eventos_compras()
        if filtro in ("", "promissorias"):
            eventos += self.eventos_promissorias()
        if filtro in ("", "pagamentos"):
            eventos += self.eventos_pagamentos()
        eventos.sort(key=lambda e: e["momento"], reverse=True)
        context.update({"eventos": eventos, "filtro": filtro, "filtros": self.FILTROS})
        return context

    @staticmethod
    def _momento(data, criado_em):
        """Datas sem hora usam o horário do registro, se for do mesmo dia, para ordenar a linha do tempo."""
        if criado_em and timezone.localtime(criado_em).date() == data:
            return criado_em
        return timezone.make_aware(datetime.combine(data, time(12)))

    def eventos_compras(self):
        vendas = (
            Venda.objects.visiveis_para(self.request.user).filter(cliente=self.object)
            .select_related("vendedor").prefetch_related("itens__produto")
        )
        return [{
            "tipo": "compra", "icone": "bag", "cor": "secondary" if v.status == Venda.Status.CANCELADA else "primary",
            "titulo": f"Compra #{v.pk}" + (" (cancelada)" if v.status == Venda.Status.CANCELADA else ""),
            "detalhes": [f"{i.quantidade}x {i.produto.nome}" for i in v.itens.all()],
            "info": v.get_forma_pagamento_display(),
            "valor": v.valor_total, "usuario": v.vendedor, "momento": v.data_venda, "hora": True,
            "link": reverse("vendas:detalhe", args=[v.pk]), "riscado": v.status == Venda.Status.CANCELADA,
        } for v in vendas]

    def eventos_promissorias(self):
        eventos = []
        promissorias = self.object.promissorias.select_related("criado_por").prefetch_related("historico__usuario", "pagamentos")
        for p in promissorias:
            eventos.append({
                "tipo": "promissoria", "icone": "receipt", "cor": "warning",
                "titulo": f"Promissória {p.numero} emitida",
                "detalhes": [f"Vencimento em {p.data_vencimento:%d/%m/%Y}"] + ([f"Referente à venda #{p.venda_id}"] if p.venda_id else []),
                "valor": p.valor, "usuario": p.criado_por, "momento": self._momento(p.data_emissao, p.criado_em),
            })
            if p.status == Promissoria.Status.PAGA and p.data_pagamento:
                ultimo = max((pg for pg in p.pagamentos.all() if not pg.cancelado), key=lambda pg: pg.criado_em, default=None)
                momento = self._momento(p.data_pagamento, ultimo.criado_em if ultimo else None)
                eventos.append({
                    "tipo": "promissoria", "icone": "check-circle", "cor": "success",
                    "titulo": f"Promissória {p.numero} quitada", "detalhes": [],
                    "valor": p.valor, "momento": momento + timedelta(microseconds=1),
                })
            for h in p.historico.all():
                if h.acao == "Cancelamento":
                    eventos.append({
                        "tipo": "promissoria", "icone": "x-circle", "cor": "secondary",
                        "titulo": f"Promissória {p.numero} cancelada",
                        "detalhes": [f"Motivo: {h.descricao}"] if h.descricao else [],
                        "usuario": h.usuario, "momento": h.data, "hora": True,
                    })
        return eventos

    def eventos_pagamentos(self):
        pagamentos = Pagamento.objects.filter(promissoria__cliente=self.object).select_related("promissoria", "recebido_por")
        return [{
            "tipo": "pagamento", "icone": "cash-coin", "cor": "secondary" if pg.cancelado else "success",
            "titulo": "Pagamento recebido" + (" (cancelado)" if pg.cancelado else ""),
            "detalhes": [f"Promissória {pg.promissoria.numero}"]
            + ([pg.observacoes] if pg.observacoes else [])
            + ([f"Motivo do cancelamento: {pg.motivo_cancelamento}"] if pg.cancelado and pg.motivo_cancelamento else []),
            "info": pg.get_forma_pagamento_display(),
            "valor": pg.valor, "usuario": pg.recebido_por, "momento": self._momento(pg.data_pagamento, pg.criado_em),
            "riscado": pg.cancelado,
        } for pg in pagamentos]


class PagamentosClienteView(PermissionRequiredMixin, DetailView):
    """Tudo o que o cliente comprou e o que ainda deve."""

    permission_required = "promissorias.view_promissoria"
    model = Cliente
    template_name = "pagamentos/cliente.html"
    context_object_name = "cliente"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = self.object
        vendas = Venda.objects.visiveis_para(self.request.user).filter(cliente=cliente)
        concluidas = vendas.concluidas()
        totais = concluidas.aggregate(quantidade=Count("id"), valor=Sum("valor_total"), ultima=Max("data_venda"))
        subtotal = ExpressionWrapper(F("quantidade") * F("preco_unitario"), output_field=DecimalField())

        context.update({
            "resumo_compras": {
                "quantidade": totais["quantidade"],
                "valor": totais["valor"] or Decimal("0"),
                "ultima": totais["ultima"],
            },
            "promissorias_abertas": cliente.promissorias.em_aberto().select_related("venda"),
            "pagamentos": (
                Pagamento.objects.filter(promissoria__cliente=cliente)
                .select_related("promissoria", "recebido_por")[:20]
            ),
            "produtos_comprados": (
                ItemVenda.objects.filter(venda__in=concluidas)
                .values("produto__nome", "produto__marca")
                .annotate(total_itens=Sum("quantidade"), valor=Sum(subtotal), ultima=Max("venda__data_venda"))
                .order_by("-total_itens", "produto__nome")
            ),
        })
        return context
