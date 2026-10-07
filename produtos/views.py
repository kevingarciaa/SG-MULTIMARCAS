from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from .models import Produto


class ProdutoListView(PermissionRequiredMixin, ListView):
    permission_required = "produtos.view_produto"
    template_name = "produtos/lista.html"
    context_object_name = "produtos"
    paginate_by = 25

    def get_queryset(self):
        produtos = Produto.objects.all()
        busca = self.request.GET.get("q", "").strip()
        if busca:
            produtos = produtos.filter(
                Q(nome__icontains=busca) | Q(marca__icontains=busca) | Q(codigo__icontains=busca)
            )
        if not self.request.GET.get("inativos"):
            produtos = produtos.ativos()
        return produtos
