from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from vendas.models import Venda

from .forms import ClienteForm
from .models import Cliente


class ClienteListView(PermissionRequiredMixin, ListView):
    permission_required = "clientes.view_cliente"
    template_name = "clientes/lista.html"
    context_object_name = "clientes"
    paginate_by = 20

    def get_queryset(self):
        clientes = Cliente.objects.all()
        busca = self.request.GET.get("q", "").strip()
        if busca:
            digitos = "".join(c for c in busca if c.isdigit())
            filtro = Q(nome__icontains=busca)
            if digitos:
                filtro |= Q(cpf__contains=digitos) | Q(telefone__contains=digitos)
            clientes = clientes.filter(filtro)
        if not self.request.GET.get("inativos"):
            clientes = clientes.ativos()
        return clientes


class ClienteDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "clientes.view_cliente"
    model = Cliente
    template_name = "clientes/detalhe.html"
    context_object_name = "cliente"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vendas"] = (
            Venda.objects.visiveis_para(self.request.user)
            .filter(cliente=self.object)
            .select_related("vendedor")[:20]
        )
        context["promissorias"] = self.object.promissorias.em_aberto()
        return context


class ClienteFormMixin(PermissionRequiredMixin):
    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/form.html"
    mensagem = ""

    def form_valid(self, form):
        resposta = super().form_valid(form)
        messages.success(self.request, self.mensagem.format(cliente=self.object))
        return resposta

    def get_success_url(self):
        return reverse("clientes:detalhe", args=[self.object.pk])


class ClienteCreateView(ClienteFormMixin, CreateView):
    permission_required = "clientes.add_cliente"
    mensagem = "Cliente {cliente} cadastrado com sucesso."

    def form_valid(self, form):
        form.instance.cadastrado_por = self.request.user
        return super().form_valid(form)


class ClienteUpdateView(ClienteFormMixin, UpdateView):
    permission_required = "clientes.change_cliente"
    mensagem = "Dados de {cliente} atualizados."
