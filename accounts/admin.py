from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Perfil

Usuario = get_user_model()


class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    max_num = 1
    fields = ("papel", "telefone")
    verbose_name = verbose_name_plural = "perfil e regras de acesso"


admin.site.unregister(Usuario)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "papel", "is_active", "last_login")
    list_filter = ("perfil__papel", "is_active", "is_superuser")
    list_select_related = ("perfil",)
    # Grupos e acesso ao /admin são definidos automaticamente pelo papel do perfil
    readonly_fields = ("groups", "is_staff", "last_login", "date_joined")

    def get_inlines(self, request, obj=None):
        # Na criação o perfil é gerado automaticamente; o papel é escolhido na tela seguinte
        return [PerfilInline] if obj else []

    @admin.display(description="papel", ordering="perfil__papel")
    def papel(self, obj):
        perfil = getattr(obj, "perfil", None)
        return perfil.get_papel_display() if perfil else "-"
