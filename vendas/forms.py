from datetime import timedelta

from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from clientes.models import Cliente
from core.forms import BootstrapFormMixin
from core.templatetags.formatacao import moeda
from produtos.models import Produto

from .models import ItemVenda, Venda


class ProdutoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj} - {moeda(obj.preco)}"


class VendaForm(BootstrapFormMixin, forms.ModelForm):
    vencimento_promissoria = forms.DateField(
        label="Vencimento da promissória", required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        help_text="Obrigatório quando o pagamento for por promissória.",
    )

    class Meta:
        model = Venda
        fields = ["cliente", "forma_pagamento", "desconto", "observacoes"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = Cliente.objects.ativos()
        self.fields["cliente"].empty_label = "Consumidor (sem cadastro)"
        self.fields["desconto"].widget.attrs.update({"min": "0", "step": "0.01"})
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
