from django.conf import settings
from django.views.generic import TemplateView

from accounts.mixins import GerenteRequiredMixin
from accounts.permissoes import eh_gerente
from core.periodos import FiltroPeriodoForm, calcular_periodo
from vendas.models import Venda

from . import services


class DashboardView(TemplateView):
    """Gerente vê a visão geral da loja; vendedor vê apenas os próprios resultados."""

    def get_template_names(self):
        if eh_gerente(self.request.user):
            return ["dashboard/gerente.html"]
        return ["dashboard/vendedor.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if eh_gerente(self.request.user):
            context.update(self.contexto_gerente())
        else:
            context.update(self.contexto_vendedor())
        return context

    def contexto_gerente(self):
        vendas = Venda.objects.concluidas()
        mes = calcular_periodo(FiltroPeriodoForm.ESTE_MES)
        return {
            "indicadores": services.indicadores_loja(),
            "periodo": mes,
            "ranking": services.ranking_vendedores(mes.filtrar(vendas)),
            "produtos": services.produtos_mais_vendidos(vendas),
            "formas": services.formas_pagamento(vendas),
            "alertas": services.alertas_promissorias(),
            "dias_alerta": settings.PROMISSORIA_DIAS_ALERTA,
            "graficos": {
                "vendasMes": services.vendas_por_mes(vendas),
                "vendasDia": services.vendas_ultimos_dias(vendas),
                "formaPagamento": services.grafico_formas_pagamento(vendas),
                "promissorias": services.promissorias_por_situacao(),
                "maisVendidos": services.grafico_produtos(vendas),
            },
        }

    def contexto_vendedor(self):
        usuario = self.request.user
        minhas_vendas = Venda.objects.concluidas().filter(vendedor=usuario)
        return {
            "indicadores": services.indicadores_vendedor(usuario),
            "ultimas_vendas": Venda.objects.filter(vendedor=usuario).select_related("cliente")[:8],
            "graficos": {"vendasDia": services.vendas_ultimos_dias(minhas_vendas)},
        }


class AnalisesView(GerenteRequiredMixin, TemplateView):
    template_name = "dashboard/analises.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtro = FiltroPeriodoForm(self.request.GET)
        periodo = filtro.periodo_escolhido()
        context.update({"filtro": filtro, "periodo": periodo, **services.analise_periodo(periodo)})
        return context
