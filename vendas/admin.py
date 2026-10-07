from django.contrib import admin

from .models import ItemVenda, Venda


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 1
    autocomplete_fields = ("produto",)


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ("id", "data_venda", "cliente", "vendedor", "forma_pagamento", "valor_total", "status")
    list_filter = ("status", "forma_pagamento", "vendedor", "data_venda")
    search_fields = ("cliente__nome", "id")
    autocomplete_fields = ("cliente",)
    readonly_fields = ("valor_total", "vendedor", "criado_em", "atualizado_em")
    inlines = [ItemVendaInline]
    date_hierarchy = "data_venda"

    def save_model(self, request, obj, form, change):
        if not obj.vendedor_id:
            obj.vendedor = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.recalcular_total()
