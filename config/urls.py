from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "SG Multimarcas - Administração"
admin.site.site_title = "SG Multimarcas"
admin.site.index_title = "Painel administrativo"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("contas/", include("accounts.urls")),
    path("clientes/", include("clientes.urls")),
    path("produtos/", include("produtos.urls")),
    path("vendas/", include("vendas.urls")),
    path("pagamentos/", include("promissorias.urls")),
    path("", include("dashboard.urls")),
]
