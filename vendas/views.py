from decimal import ROUND_HALF_UP, Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.permissoes import eh_gerente
from core.periodos import FiltroPeriodoForm
from promissorias.models import Promissoria

from .forms import ItemVendaFormSet, VendaForm
from .models import Venda


class VendaListView(PermissionRequiredMixin, ListView):
    """Vendedor: lista apenas as próprias vendas. Gerente: lista todas e pode filtrar por vendedor."""

    permission_required = "vendas.view_venda"
    template_name = "vendas/lista.html"
    context_object_name = "vendas"
    paginate_by = 20

    def get_queryset(self):
        self.filtro = FiltroPeriodoForm(self.request.GET, padrao="", permitir_todos=True)
        self.periodo = self.filtro.periodo_escolhido()

        vendas = Venda.objects.visiveis_para(self.request.user).select_related("cliente", "vendedor")
        if self.periodo:
            vendas = self.periodo.filtrar(vendas)

        busca = self.request.GET.get("q", "").strip()
        if busca:
            filtro = Q(cliente__nome__icontains=busca)
            if busca.isdigit():
                filtro |= Q(pk=int(busca))
            vendas = vendas.filter(filtro)

        self.vendedor_id = self.request.GET.get("vendedor", "")
        if eh_gerente(self.request.user) and self.vendedor_id.isdigit():
            vendas = vendas.filter(vendedor_id=int(self.vendedor_id))
        return vendas

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        totais = self.object_list.concluidas().aggregate(quantidade=Count("id"), valor=Sum("valor_total"))
        valor = totais["valor"] or Decimal("0")
        context.update({
            "filtro": self.filtro,
            "periodo": self.periodo,
            "totais": {
                "quantidade": totais["quantidade"],
                "valor": valor,
                "ticket_medio": valor / totais["quantidade"] if totais["quantidade"] else Decimal("0"),
            },
        })
        if eh_gerente(self.request.user):
            context["vendedores"] = (
                get_user_model().objects.filter(Q(perfil__papel="vendedor") | Q(vendas__isnull=False))
                .distinct().order_by("first_name", "username")
            )
            context["vendedor_id"] = self.vendedor_id
        return context


class VendaDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "vendas.view_venda"
    template_name = "vendas/detalhe.html"
    context_object_name = "venda"

    def get_queryset(self):
        # Venda de outro vendedor responde 404, como se não existisse
        return (
            Venda.objects.visiveis_para(self.request.user)
            .select_related("cliente", "vendedor")
            .prefetch_related("itens__produto", "promissorias")
        )


class VendaCreateView(PermissionRequiredMixin, View):
    permission_required = "vendas.add_venda"
    template_name = "vendas/form.html"
    prefixo_itens = "itens"

    def get(self, request):
        form = VendaForm(initial={"cliente": request.GET.get("cliente")})
        formset = ItemVendaFormSet(prefix=self.prefixo_itens)
        return self.exibir(form, formset)

    def post(self, request):
        form = VendaForm(request.POST)
        formset = ItemVendaFormSet(request.POST, prefix=self.prefixo_itens)
        if form.is_valid() and formset.is_valid() and self.validar_total(form, formset):
            venda = self.salvar(form, formset)
            messages.success(request, f"Venda #{venda.pk} registrada com sucesso.")
            return redirect("vendas:detalhe", pk=venda.pk)
        return self.exibir(form, formset)

    def exibir(self, form, formset):
        return render(self.request, self.template_name, {"form": form, "formset": formset})

    def validar_total(self, form, formset):
        subtotal = sum(
            (item.cleaned_data["produto"].preco * item.cleaned_data["quantidade"]
             for item in formset.forms
             if item.cleaned_data and not item.cleaned_data.get("DELETE")),
            Decimal("0"),
        )
        percentual = form.cleaned_data.get("desconto_percentual") or Decimal("0")
        desconto = (subtotal * percentual / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        promissoria = form.cleaned_data["forma_pagamento"] == Venda.FormaPagamento.PROMISSORIA
        if promissoria and desconto >= subtotal:
            form.add_error("desconto_percentual", "Venda em promissória precisa ter valor maior que zero.")
            return False
        form.instance.desconto = desconto
        return True

    @transaction.atomic
    def salvar(self, form, formset):
        usuario = self.request.user
        venda = form.save(commit=False)
        venda.vendedor = usuario
        venda.save()
        formset.instance = venda
        formset.save()
        venda.refresh_from_db()

        if venda.forma_pagamento == Venda.FormaPagamento.PROMISSORIA:
            Promissoria(
                cliente=venda.cliente, venda=venda, valor=venda.valor_total,
                data_vencimento=form.cleaned_data["vencimento_promissoria"],
            ).save(usuario=usuario)
        return venda
