from django.db import models


class Processo(models.Model):
    STATUS_ABERTO = "Aberto"
    STATUS_FECHADO = "Fechado"

    STATUS_CHOICES = [
        (STATUS_ABERTO, "Aberto"),
        (STATUS_FECHADO, "Fechado"),
    ]

    nome = models.TextField()
    area = models.TextField(blank=True, null=True)
    senioridade = models.TextField(blank=True, null=True)
    job_title = models.TextField(blank=True, null=True)
    admission_category = models.TextField(blank=True, null=True)
    tipo = models.TextField(blank=True, default="")
    descricao = models.TextField(blank=True, default="")
    local = models.TextField(blank=True, null=True)
    status = models.TextField(choices=STATUS_CHOICES, default=STATUS_ABERTO)
    data_inicio = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "processos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Candidato(models.Model):
    nome = models.TextField()
    email = models.EmailField(unique=True)
    linkedin = models.TextField(blank=True, null=True)
    greenhouse_id = models.TextField(blank=True, null=True)
    pbix_file = models.TextField(blank=True, null=True)
    optional_file = models.TextField(blank=True, null=True)
    pais = models.TextField(blank=True, default="")
    nivel = models.TextField(blank=True, default="")
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidatos"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.email})"


class Aplicacao(models.Model):
    candidato = models.ForeignKey(Candidato, on_delete=models.CASCADE, related_name="aplicacoes")
    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="aplicacoes")
    greenhouse_id = models.TextField(blank=True, null=True)
    pbix_file = models.TextField(blank=True, null=True)
    optional_file = models.TextField(blank=True, null=True)
    timestamp_aplicacao = models.DateTimeField(auto_now_add=True)
    data_importacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "aplicacoes"
        unique_together = ("candidato", "processo")
        ordering = ["-timestamp_aplicacao"]


class Avaliacao(models.Model):
    PRIORIZACAO_CHOICES = [
        ("Prioridade 1", "Strong Yes"),
        ("Prioridade 2", "Yes"),
        ("Não priorizar", "Não priorizar"),
    ]

    aplicacao = models.ForeignKey(Aplicacao, on_delete=models.CASCADE, related_name="avaliacoes")
    nota_final = models.DecimalField(max_digits=5, decimal_places=2)
    avaliador = models.TextField(blank=True, null=True)
    comentario_final = models.TextField(blank=True, null=True)
    priorizacao = models.TextField(choices=PRIORIZACAO_CHOICES, default="Não priorizar")
    gh_atualizada = models.BooleanField(default=False)
    finalizada = models.BooleanField(default=False)
    data_avaliacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "avaliacoes"
        ordering = ["-data_avaliacao"]


class AvaliacaoCriterio(models.Model):
    avaliacao = models.ForeignKey(Avaliacao, on_delete=models.CASCADE, related_name="criterios")
    bloco = models.TextField()
    criterio = models.TextField()
    nota = models.DecimalField(max_digits=4, decimal_places=1)
    justificativa = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "avaliacoes_criterios"
        ordering = ["bloco", "criterio"]


class AllowedEmail(models.Model):
    ROLE_CHOICES = [
        ("admin", "admin"),
        ("user", "user"),
        ("viewer", "viewer"),
    ]

    email = models.EmailField(unique=True)
    role = models.TextField(choices=ROLE_CHOICES, default="user")
    added_by = models.TextField(blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "allowed_emails"
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.email} ({self.role})"
