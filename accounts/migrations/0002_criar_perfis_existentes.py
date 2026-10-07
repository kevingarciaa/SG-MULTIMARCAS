from django.conf import settings
from django.db import migrations


def criar_perfis(apps, schema_editor):
    """Cria perfil para usuários que já existiam antes do model Perfil.

    Os grupos/permissões são aplicados depois com: python manage.py criar_grupos
    """
    Usuario = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    Perfil = apps.get_model("accounts", "Perfil")
    for usuario in Usuario.objects.filter(perfil__isnull=True):
        papel = "administrador" if usuario.is_superuser else "vendedor"
        Perfil.objects.create(usuario=usuario, papel=papel)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(criar_perfis, migrations.RunPython.noop),
    ]
