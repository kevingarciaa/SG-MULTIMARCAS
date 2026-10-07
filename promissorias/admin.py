from django.contrib import admin

from .models import HistoricoPromissoria, Pagamento, Promissoria


class PagamentoInline(admin.TabularInline):
    model = Pagamento
    extra = 0
    fields = ("data_pagamento", "valor", "forma_pagamento", "recebido_por", "cancelado")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class HistoricoInline(admin.TabularInline):
    model = HistoricoPromissoria
    extra = 0
    fields = ("data", "acao", "descricao", "usuario")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Promissoria)
class PromissoriaAdmin(admin.ModelAdmin):
    list_display = (
        "numero", "cliente", "valor", "valor_pago", "data_vencimento", "situacao_display", "dias_atraso",
    )
    list_filter = ("status", "data_vencimento")
    search_fields = ("numero", "cliente__nome", "cliente__cpf")
    autocomplete_fields = ("cliente", "venda")
    readonly_fields = ("numero", "valor_pago", "data_pagamento", "criado_por", "criado_em", "atualizado_em")
    inlines = [PagamentoInline, HistoricoInline]

    @admin.display(description="situação")
    def situacao_display(self, obj):
        return obj.situacao_display

    @admin.display(description="dias de atraso")
    def dias_atraso(self, obj):
        return obj.dias_atraso or "-"

    def save_model(self, request, obj, form, change):
        obj.save(usuario=request.user)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ("promissoria", "data_pagamento", "valor", "forma_pagamento", "recebido_por", "cancelado")
    list_filter = ("cancelado", "forma_pagamento", "data_pagamento")
    search_fields = ("promissoria__numero", "promissoria__cliente__nome")
    autocomplete_fields = ("promissoria",)
    readonly_fields = ("recebido_por", "cancelado", "motivo_cancelamento", "criado_em", "atualizado_em")

    def get_readonly_fields(self, request, obj=None):
        if obj:  # pagamento registrado não é editado; se errado, deve ser cancelado
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if not obj.recebido_por_id:
            obj.recebido_por = request.user
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return False
