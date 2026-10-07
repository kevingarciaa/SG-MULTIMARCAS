from django.db import migrations


def _converter(apps, papel_antigo, papel_novo, grupo_antigo, grupo_novo):
    Perfil = apps.get_model("accounts", "Perfil")
    Group = apps.get_model("auth", "Group")
    Perfil.objects.filter(papel=papel_antigo).update(papel=papel_novo)
    if not Group.objects.filter(name=grupo_novo).exists():
        Group.objects.filter(name=grupo_antigo).update(name=grupo_novo)


def administrador_para_gerente(apps, schema_editor):
    """O papel "Administrador" passa a se chamar "Gerente" (mesmas regras de acesso)."""
    _converter(apps, "administrador", "gerente", "Administrador", "Gerente")


def gerente_para_administrador(apps, schema_editor):
    _converter(apps, "gerente", "administrador", "Gerente", "Administrador")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_alter_perfil_papel"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(administrador_para_gerente, gerente_para_administrador),
    ]
