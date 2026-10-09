from django.conf import settings
from django.shortcuts import redirect
from django.views.generic import TemplateView

from accounts.mixins import GerenteRequiredMixin
from accounts.permissoes import eh_gerente
from core.periodos import FiltroPeriodoForm, calcular_periodo
from vendas.models import Venda

from . import services


class DashboardView(TemplateView):
    """Página inicial: gerente vê a visão geral da loja; vendedor vai direto para a nova venda."""

    template_name = "dashboard/gerente.html"

    def get(self, request, *args, **kwargs):
        if not eh_gerente(request.user):
            return redirect("vendas:nova")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendas = Venda.objects.concluidas()
        mes = calcular_periodo(FiltroPeriodoForm.ESTE_MES)
        formas = services.formas_pagamento(vendas)
        context.update({
            "indicadores": services.indicadores_loja(),
            "periodo": mes,
            "ranking": services.ranking_vendedores(mes.filtrar(vendas)),
            "produtos": services.produtos_mais_vendidos(vendas),
            "formas": formas,
            "alertas": services.alertas_promissorias(),
            "dias_alerta": settings.PROMISSORIA_DIAS_ALERTA,
            "graficos": {
                "vendasDia": services.vendas_ultimos_dias(vendas),
                "formaPagamento": services.grafico_formas_pagamento(formas),
                "promissorias": services.promissorias_por_situacao(),
            },
        })
        return context


class AnalisesView(GerenteRequiredMixin, TemplateView):
    template_name = "dashboard/analises.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtro = FiltroPeriodoForm(self.request.GET)
        periodo = filtro.periodo_escolhido()
        context.update({"filtro": filtro, "periodo": periodo, **services.analise_periodo(periodo)})
        return context
