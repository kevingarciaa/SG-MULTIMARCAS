from django import forms

from core.forms import BootstrapFormMixin
from core.templatetags.formatacao import moeda

from .models import Pagamento


class PromissoriaChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        situacao = " (vencida)" if obj.esta_vencida else ""
        return f"{obj.numero} · vence {obj.data_vencimento:%d/%m/%Y}{situacao} · falta {moeda(obj.valor_em_aberto)}"


class PagamentoForm(BootstrapFormMixin, forms.ModelForm):
    promissoria = PromissoriaChoiceField(queryset=None, label="Promissória", empty_label=None)

    class Meta:
        model = Pagamento
        fields = ["promissoria", "valor", "data_pagamento", "forma_pagamento", "observacoes"]
        widgets = {
            "valor": forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "inputmode": "decimal", "placeholder": "0,00"}),
            "data_pagamento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, cliente, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["promissoria"].queryset = cliente.promissorias.em_aberto()
        self.fields["valor"].help_text = "Quanto o cliente está pagando agora. Pode ser só uma parte do que falta."
