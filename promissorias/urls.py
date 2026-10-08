from django.urls import path

from . import views

app_name = "pagamentos"

urlpatterns = [
    path("", views.PagamentosListView.as_view(), name="lista"),
    path("cliente/<int:pk>/", views.PagamentosClienteView.as_view(), name="cliente"),
    path("cliente/<int:pk>/compras/", views.ComprasClienteView.as_view(), name="compras"),
    path("cliente/<int:pk>/historico/", views.HistoricoClienteView.as_view(), name="historico"),
    path("cliente/<int:pk>/pagar/", views.RegistrarPagamentoView.as_view(), name="registrar"),
]
