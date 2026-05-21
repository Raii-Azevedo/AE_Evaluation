from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    """
    Adiciona a coluna data_cadastro à tabela candidatos.
    A tabela foi criada por uma versão antiga do database.py que não tinha
    essa coluna, e o --fake-initial não a adicionou.
    Existing rows receberão o timestamp atual como valor padrão.
    """

    dependencies = [
        ("core", "0002_fix_avaliacao_data_auto_now"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidato",
            name="data_cadastro",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
