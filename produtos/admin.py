from django.contrib import admin

from .models import HistoricoProduto, Produto


class HistoricoInline(admin.TabularInline):
    model = HistoricoProduto
    extra = 0
    fields = ("data", "acao", "descricao", "usuario")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "codigo", "marca", "preco", "estoque", "ativo")
    list_filter = ("ativo", "marca")
    list_editable = ("ativo",)
    search_fields = ("nome", "codigo", "marca")
    readonly_fields = ("criado_em", "atualizado_em")
    inlines = [HistoricoInline]

    def save_model(self, request, obj, form, change):
        obj.save(usuario=request.user)
