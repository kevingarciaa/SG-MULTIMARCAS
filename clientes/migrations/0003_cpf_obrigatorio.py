import core.validators
from django.db import migrations, models


def exigir_cpf_preenchido(apps, schema_editor):
    Cliente = apps.get_model("clientes", "Cliente")
    sem_cpf = list(Cliente.objects.filter(models.Q(cpf__isnull=True) | models.Q(cpf="")).values_list("id", "nome"))
    if sem_cpf:
        lista = "\n".join(f"  - #{pk} {nome}" for pk, nome in sem_cpf)
        raise RuntimeError(
            "O CPF passou a ser obrigatório, mas estes clientes estão sem CPF. "
            f"Preencha o CPF deles antes de rodar a migração:\n{lista}"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0002_cliente_cadastrado_por'),
    ]

    operations = [
        migrations.RunPython(exigir_cpf_preenchido, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='cliente',
            name='cpf',
            field=models.CharField(help_text='Com ou sem pontuação. É salvo somente com números.', max_length=14, unique=True, validators=[core.validators.validar_cpf], verbose_name='CPF'),
        ),
    ]
