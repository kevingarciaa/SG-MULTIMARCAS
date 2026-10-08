from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .forms import ProdutoForm
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


class ProdutoFormMixin(PermissionRequiredMixin):
    model = Produto
    form_class = ProdutoForm
    template_name = "produtos/form.html"
    success_url = reverse_lazy("produtos:lista")
    mensagem = ""

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save(usuario=self.request.user)
        messages.success(self.request, self.mensagem.format(produto=self.object))
        return HttpResponseRedirect(self.get_success_url())


class ProdutoCreateView(ProdutoFormMixin, CreateView):
    permission_required = "produtos.add_produto"
    mensagem = "Produto {produto} cadastrado com sucesso."


class ProdutoUpdateView(ProdutoFormMixin, UpdateView):
    permission_required = "produtos.change_produto"
    mensagem = "Produto {produto} atualizado."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["historico"] = self.object.historico.select_related("usuario")[:50]
        return context
