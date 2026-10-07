from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from core.forms import BootstrapFormMixin


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuário"
        self.fields["username"].widget.attrs.update({"placeholder": "Seu usuário", "autofocus": True})
        self.fields["password"].widget.attrs.update({"placeholder": "Sua senha"})


class AlterarSenhaForm(BootstrapFormMixin, PasswordChangeForm):
    pass
