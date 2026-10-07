from django.urls import path

from . import views

app_name = "produtos"

urlpatterns = [
    path("", views.ProdutoListView.as_view(), name="lista"),
]
