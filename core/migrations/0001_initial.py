from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AllowedEmail",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("role", models.TextField(choices=[("admin", "admin"), ("user", "user"), ("viewer", "viewer")], default="user")),
                ("added_by", models.TextField(blank=True, null=True)),
                ("added_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "allowed_emails", "ordering": ["-added_at"]},
        ),
        migrations.CreateModel(
            name="Candidato",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.TextField()),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("linkedin", models.TextField(blank=True, null=True)),
                ("greenhouse_id", models.TextField(blank=True, null=True)),
                ("pbix_file", models.TextField(blank=True, null=True)),
                ("optional_file", models.TextField(blank=True, null=True)),
                ("pais", models.TextField(blank=True, default="")),
                ("nivel", models.TextField(blank=True, default="")),
                ("data_cadastro", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "candidatos", "ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="Processo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.TextField()),
                ("area", models.TextField(blank=True, null=True)),
                ("senioridade", models.TextField(blank=True, null=True)),
                ("job_title", models.TextField(blank=True, null=True)),
                ("admission_category", models.TextField(blank=True, null=True)),
                ("tipo", models.TextField(blank=True, default="")),
                ("descricao", models.TextField(blank=True, default="")),
                ("local", models.TextField(blank=True, null=True)),
                ("status", models.TextField(choices=[("Aberto", "Aberto"), ("Fechado", "Fechado")], default="Aberto")),
                ("data_inicio", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "processos", "ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="Aplicacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("greenhouse_id", models.TextField(blank=True, null=True)),
                ("pbix_file", models.TextField(blank=True, null=True)),
                ("optional_file", models.TextField(blank=True, null=True)),
                ("timestamp_aplicacao", models.DateTimeField(auto_now_add=True)),
                ("data_importacao", models.DateTimeField(auto_now_add=True)),
                ("candidato", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="aplicacoes", to="core.candidato")),
                ("processo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="aplicacoes", to="core.processo")),
            ],
            options={"db_table": "aplicacoes", "ordering": ["-timestamp_aplicacao"], "unique_together": {("candidato", "processo")}},
        ),
        migrations.CreateModel(
            name="Avaliacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nota_final", models.DecimalField(decimal_places=2, max_digits=5)),
                ("avaliador", models.TextField(blank=True, null=True)),
                ("comentario_final", models.TextField(blank=True, null=True)),
                ("priorizacao", models.TextField(choices=[("Strong Yes", "Strong Yes"), ("Yes", "Yes"), ("Maybe", "Maybe"), ("No", "No"), ("Não priorizar", "Não priorizar")], default="Não priorizar")),
                ("gh_atualizada", models.BooleanField(default=False)),
                ("data_avaliacao", models.DateTimeField(auto_now_add=True)),
                ("aplicacao", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="avaliacoes", to="core.aplicacao")),
            ],
            options={"db_table": "avaliacoes", "ordering": ["-data_avaliacao"]},
        ),
        migrations.CreateModel(
            name="AvaliacaoCriterio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bloco", models.TextField()),
                ("criterio", models.TextField()),
                ("nota", models.DecimalField(decimal_places=1, max_digits=4)),
                ("justificativa", models.TextField(blank=True, null=True)),
                ("avaliacao", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="criterios", to="core.avaliacao")),
            ],
            options={"db_table": "avaliacoes_criterios", "ordering": ["bloco", "criterio"]},
        ),
    ]
