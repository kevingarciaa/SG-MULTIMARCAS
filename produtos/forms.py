from django import forms

from core.forms import BootstrapFormMixin

from .models import Produto


class ProdutoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Produto
        fields = ["nome", "marca", "codigo", "preco", "estoque", "descricao", "ativo"]
        widgets = {
            "preco": forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "inputmode": "decimal"}),
            "estoque": forms.NumberInput(attrs={"min": "0"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {"ativo": "Produtos inativos não aparecem na tela de nova venda."}
