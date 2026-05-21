from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Muda data_avaliacao de auto_now_add=True para auto_now=True.
    Com auto_now_add, o campo não era atualizado ao re-salvar a avaliação.
    Com auto_now, o campo é atualizado sempre que o objeto é salvo.
    """

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="avaliacao",
            name="data_avaliacao",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
