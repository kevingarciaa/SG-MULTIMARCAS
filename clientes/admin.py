from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf_formatado", "telefone_formatado", "cidade", "ativo")
    list_filter = ("ativo", "cidade")
    search_fields = ("nome", "cpf", "telefone", "email")
    readonly_fields = ("criado_em", "atualizado_em")
