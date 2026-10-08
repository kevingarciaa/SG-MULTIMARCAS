from datetime import timedelta
from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from clientes.models import Cliente
from core.forms import BootstrapFormMixin
from core.templatetags.formatacao import moeda
from produtos.models import Produto

from .models import ItemVenda, Venda


class ProdutoSelect(forms.Select):
    """Inclui preço e nome em cada opção para o resumo da venda calcular o total no navegador."""

    def create_option(self, name, value, *args, **kwargs):
        opcao = super().create_option(name, value, *args, **kwargs)
        produto = getattr(value, "instance", None)
        if produto is not None:
            opcao["attrs"].update({"data-preco": str(produto.preco), "data-nome": str(produto)})
        return opcao


class ProdutoChoiceField(forms.ModelChoiceField):
    widget = ProdutoSelect

    def label_from_instance(self, obj):
        return f"{obj} - {moeda(obj.preco)}"


class VendaForm(BootstrapFormMixin, forms.ModelForm):
    vencimento_promissoria = forms.DateField(
        label="Vencimento da promissória", required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        help_text="Obrigatório quando o pagamento for por promissória.",
    )
    desconto_percentual = forms.DecimalField(
        label="Desconto (%)", required=False, min_value=Decimal("0"), max_value=Decimal("100"),
        max_digits=5, decimal_places=2,
        widget=forms.NumberInput(attrs={"min": "0", "max": "100", "step": "0.01", "placeholder": "0"}),
        help_text="Porcentagem sobre o valor dos produtos.",
    )

    class Meta:
        model = Venda
        fields = ["cliente", "forma_pagamento", "observacoes"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = Cliente.objects.ativos()
        self.fields["cliente"].required = True
        self.fields["cliente"].empty_label = "Selecione o cliente"
        self.fields["cliente"].help_text = ""
        self.fields["cliente"].error_messages["required"] = (
            "Selecione o cliente. Se ele ainda não tem cadastro, cadastre-o antes de registrar a venda."
        )
        self.fields["vencimento_promissoria"].initial = timezone.localdate() + timedelta(days=30)

    def clean(self):
        dados = super().clean()
        if dados.get("forma_pagamento") == Venda.FormaPagamento.PROMISSORIA:
            vencimento = dados.get("vencimento_promissoria")
            if not vencimento:
                self.add_error("vencimento_promissoria", "Informe o vencimento da promissória.")
            elif vencimento < timezone.localdate():
                self.add_error("vencimento_promissoria", "O vencimento não pode ser uma data passada.")
        return dados


class ItemVendaForm(BootstrapFormMixin, forms.ModelForm):
    produto = ProdutoChoiceField(queryset=Produto.objects.ativos(), label="Produto")

    class Meta:
        model = ItemVenda
        fields = ["produto", "quantidade"]
        widgets = {"quantidade": forms.NumberInput(attrs={"min": "1"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quantidade"].initial = 1


ItemVendaFormSet = inlineformset_factory(
    Venda, ItemVenda, form=ItemVendaForm,
    extra=0, min_num=1, validate_min=True, can_delete=True,
)
