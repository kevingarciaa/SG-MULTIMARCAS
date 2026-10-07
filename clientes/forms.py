from django import forms

from core.forms import BootstrapFormMixin

from .models import Cliente


class ClienteForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "nome", "cpf", "telefone", "email", "data_nascimento",
            "endereco", "bairro", "cidade", "observacoes", "ativo",
        ]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
            "telefone": forms.TextInput(attrs={"placeholder": "(11) 98765-4321", "inputmode": "tel"}),
            "cpf": forms.TextInput(attrs={"placeholder": "000.000.000-00", "inputmode": "numeric"}),
        }
        help_texts = {"ativo": "Clientes inativos não aparecem na tela de nova venda."}
