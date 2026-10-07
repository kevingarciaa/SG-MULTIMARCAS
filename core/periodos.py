"""Filtro de período usado nas listagens e nas análises (Hoje, Últimos 7 dias etc.)."""

from dataclasses import dataclass
from datetime import date, timedelta

from django import forms
from django.utils import timezone

from .forms import BootstrapFormMixin


@dataclass(frozen=True)
class Periodo:
    inicio: date
    fim: date
    descricao: str
    mensal: bool = False

    @property
    def dias(self):
        return (self.fim - self.inicio).days + 1

    def anterior(self):
        """Período usado na comparação.

        Filtros mensais comparam com os mesmos dias do mês anterior (o mês inteiro,
        no caso de "Mês anterior"); os demais, com o mesmo número de dias logo antes.
        """
        if self.mensal:
            fim_mes_passado = self.inicio - timedelta(days=1)
            inicio = fim_mes_passado.replace(day=1)
            fim = min(inicio + (self.fim - self.inicio), fim_mes_passado)
            return Periodo(inicio, fim, "período anterior", mensal=True)
        fim = self.inicio - timedelta(days=1)
        return Periodo(fim - timedelta(days=self.dias - 1), fim, "período anterior")

    def filtrar(self, queryset, campo="data_venda"):
        return queryset.filter(**{f"{campo}__date__range": (self.inicio, self.fim)})


class FiltroPeriodoForm(BootstrapFormMixin, forms.Form):
    HOJE, SETE_DIAS, ESTE_MES, MES_ANTERIOR, PERSONALIZADO = "hoje", "7dias", "mes", "mes_anterior", "personalizado"
    OPCOES = [
        (HOJE, "Hoje"),
        (SETE_DIAS, "Últimos 7 dias"),
        (ESTE_MES, "Este mês"),
        (MES_ANTERIOR, "Mês anterior"),
        (PERSONALIZADO, "Período personalizado"),
    ]

    periodo = forms.ChoiceField(label="Período", required=False)
    inicio = forms.DateField(label="De", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    fim = forms.DateField(label="Até", required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, padrao=ESTE_MES, permitir_todos=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.padrao = padrao
        opcoes = list(self.OPCOES)
        if permitir_todos:
            opcoes.insert(0, ("", "Todo o período"))
        self.fields["periodo"].choices = opcoes
        self.fields["periodo"].initial = padrao

    def clean(self):
        dados = super().clean()
        if dados.get("periodo") == self.PERSONALIZADO:
            inicio, fim = dados.get("inicio"), dados.get("fim")
            if not inicio or not fim:
                raise forms.ValidationError("Informe a data inicial e a final do período personalizado.")
            if inicio > fim:
                raise forms.ValidationError("A data inicial deve ser anterior à data final.")
        return dados

    def periodo_escolhido(self):
        """Retorna o Periodo selecionado, ou None para "Todo o período"."""
        if self.is_bound and self.is_valid():
            chave = self.cleaned_data.get("periodo", "") if "periodo" in self.data else self.padrao
            inicio, fim = self.cleaned_data.get("inicio"), self.cleaned_data.get("fim")
        else:
            chave, inicio, fim = self.padrao, None, None
        return calcular_periodo(chave, inicio, fim)


def calcular_periodo(chave, inicio=None, fim=None):
    hoje = timezone.localdate()
    if chave == FiltroPeriodoForm.HOJE:
        return Periodo(hoje, hoje, "Hoje")
    if chave == FiltroPeriodoForm.SETE_DIAS:
        return Periodo(hoje - timedelta(days=6), hoje, "Últimos 7 dias")
    if chave == FiltroPeriodoForm.ESTE_MES:
        return Periodo(hoje.replace(day=1), hoje, "Este mês", mensal=True)
    if chave == FiltroPeriodoForm.MES_ANTERIOR:
        fim_anterior = hoje.replace(day=1) - timedelta(days=1)
        return Periodo(fim_anterior.replace(day=1), fim_anterior, "Mês anterior", mensal=True)
    if chave == FiltroPeriodoForm.PERSONALIZADO and inicio and fim:
        return Periodo(inicio, fim, f"{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}")
    return None
