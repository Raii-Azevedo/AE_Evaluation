from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_add_candidato_data_cadastro"),
    ]

    operations = [
        migrations.AddField(
            model_name="avaliacao",
            name="finalizada",
            field=models.BooleanField(default=False),
        ),
    ]
