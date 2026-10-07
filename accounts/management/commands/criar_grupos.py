from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import Perfil
from accounts.permissoes import configurar_grupos


class Command(BaseCommand):
    help = "Cria/atualiza os grupos de papel e reaplica as regras de acesso de todos os perfis."

    def handle(self, *args, **options):
        grupos = configurar_grupos()
        for nome, grupo in grupos.items():
            self.stdout.write(f"Grupo {nome}: {grupo.permissions.count()} permissões.")

        total = 0
        for usuario in get_user_model().objects.all():
            perfil, _ = Perfil.objects.get_or_create(usuario=usuario, defaults={"papel": Perfil.papel_inicial(usuario)})
            perfil.aplicar_regras()
            total += 1

        self.stdout.write(self.style.SUCCESS(f"Regras aplicadas a {total} usuário(s)."))
