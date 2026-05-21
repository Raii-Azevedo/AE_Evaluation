from django.contrib import admin

from .models import AllowedEmail, Aplicacao, Avaliacao, AvaliacaoCriterio, Candidato, Processo


@admin.register(Processo)
class ProcessoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "area", "job_title", "status", "data_inicio")
    list_filter = ("status", "area")
    search_fields = ("nome", "job_title", "admission_category")


@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "email", "data_cadastro")
    search_fields = ("nome", "email")


@admin.register(Aplicacao)
class AplicacaoAdmin(admin.ModelAdmin):
    list_display = ("id", "processo", "candidato", "timestamp_aplicacao")
    list_filter = ("processo",)


class AvaliacaoCriterioInline(admin.TabularInline):
    model = AvaliacaoCriterio
    extra = 0


@admin.register(Avaliacao)
class AvaliacaoAdmin(admin.ModelAdmin):
    list_display = ("id", "aplicacao", "nota_final", "avaliador", "priorizacao", "gh_atualizada", "data_avaliacao")
    list_filter = ("priorizacao", "gh_atualizada")
    inlines = [AvaliacaoCriterioInline]


@admin.register(AllowedEmail)
class AllowedEmailAdmin(admin.ModelAdmin):
    list_display = ("email", "role", "added_by", "added_at")
    search_fields = ("email",)
