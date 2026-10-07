from django.contrib import admin

from .models import Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "codigo", "marca", "preco", "estoque", "ativo")
    list_filter = ("ativo", "marca")
    list_editable = ("ativo",)
    search_fields = ("nome", "codigo", "marca")
    readonly_fields = ("criado_em", "atualizado_em")
