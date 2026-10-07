from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from .forms import AlterarSenhaForm, LoginForm

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "alterar-senha/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/alterar_senha.html",
            form_class=AlterarSenhaForm,
            success_url=reverse_lazy("accounts:alterar_senha_ok"),
        ),
        name="alterar_senha",
    ),
    path(
        "alterar-senha/ok/",
        auth_views.PasswordChangeDoneView.as_view(template_name="accounts/alterar_senha_ok.html"),
        name="alterar_senha_ok",
    ),
]
