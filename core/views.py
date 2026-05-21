from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .criterios import get_criterios_por_area
from .forms import AllowedEmailForm, CandidatoAplicacaoForm, EmailOnlyLoginForm, ProcessoForm
from .models import AllowedEmail, Aplicacao, Avaliacao, AvaliacaoCriterio, Candidato, Processo


def _get_role(user):
    email = (user.email or "").strip().lower()
    record = AllowedEmail.objects.filter(email__iexact=email).first()
    return record.role if record else None


def _can_edit(user):
    role = _get_role(user)
    return role in {"admin", "user"} or user.is_superuser


def _is_admin(user):
    role = _get_role(user)
    return role == "admin" or user.is_superuser


def allowed_email_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not AllowedEmail.objects.filter(email__iexact=(request.user.email or "")).exists() and not request.user.is_superuser:
            messages.error(request, "Seu email nao esta autorizado.")
            logout(request)
            return redirect("login")
        return view_func(request, *args, **kwargs)

    return _wrapped


def email_login(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = EmailOnlyLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        user = authenticate(request, email=email)
        if user is None:
            messages.error(request, "Email nao autorizado.")
        else:
            login(request, user)
            messages.success(request, "Login realizado com sucesso.")
            return redirect("home")

    return render(request, "registration/login.html", {"form": form})


def email_logout(request):
    logout(request)
    return redirect("login")


@allowed_email_required
def home(request):
    processos = Processo.objects.all().order_by("nome")
    processo_form = ProcessoForm(request.POST or None)

    if request.method == "POST" and "criar_processo" in request.POST:
        if not _can_edit(request.user):
            return HttpResponseForbidden("Sem permissao de edicao")
        if processo_form.is_valid():
            novo = processo_form.save(commit=False)
            novo.status = Processo.STATUS_ABERTO
            novo.save()
            messages.success(request, f"Processo '{novo.nome}' criado com sucesso.")
            return redirect("home")

    stats = {
        "processos": processos.count(),
        "candidatos": Candidato.objects.count(),
        "aplicacoes": Aplicacao.objects.count(),
        "avaliacoes": Avaliacao.objects.count(),
        "media": Avaliacao.objects.aggregate(media=Avg("nota_final"))["media"] or 0,
    }

    context = {
        "processos": processos,
        "stats": stats,
        "processo_form": processo_form,
        "can_edit": _can_edit(request.user),
        "is_admin": _is_admin(request.user),
    }
    return render(request, "core/home.html", context)


@allowed_email_required
def processo_detail(request, processo_id):
    processo = get_object_or_404(Processo, pk=processo_id)
    candidato_form = CandidatoAplicacaoForm()
    status = request.GET.get("status", "todos")

    aplicacoes = (
        Aplicacao.objects.filter(processo=processo)
        .select_related("candidato")
        .prefetch_related("avaliacoes")
        .order_by("candidato__nome")
    )

    if status == "pendentes":
        aplicacoes = aplicacoes.annotate(total_avaliacoes=Count("avaliacoes")).filter(total_avaliacoes=0)
    elif status == "avaliados":
        aplicacoes = aplicacoes.annotate(total_avaliacoes=Count("avaliacoes")).filter(total_avaliacoes__gt=0)

    rows = []
    for app in aplicacoes:
        ultima = app.avaliacoes.order_by("-data_avaliacao").first()
        rows.append({"app": app, "avaliacao": ultima})

    stats = Aplicacao.objects.filter(processo=processo).aggregate(
        pendentes=Count("id", filter=Q(avaliacoes__isnull=True), distinct=True),
        avaliados=Count("id", filter=Q(avaliacoes__isnull=False), distinct=True),
    )

    context = {
        "processo": processo,
        "rows": rows,
        "status": status,
        "stats": stats,
        "candidato_form": candidato_form,
        "can_edit": _can_edit(request.user),
    }
    return render(request, "core/processo_detail.html", context)


@allowed_email_required
def toggle_processo(request, processo_id):
    if request.method != "POST" or not _can_edit(request.user):
        return HttpResponseForbidden("Operacao nao permitida")

    processo = get_object_or_404(Processo, pk=processo_id)
    processo.status = Processo.STATUS_FECHADO if processo.status == Processo.STATUS_ABERTO else Processo.STATUS_ABERTO
    processo.save(update_fields=["status"])
    messages.success(request, f"Status do processo atualizado para {processo.status}.")
    return redirect("processo_detail", processo_id=processo.id)


@allowed_email_required
def add_candidato(request, processo_id):
    if request.method != "POST" or not _can_edit(request.user):
        return HttpResponseForbidden("Operacao nao permitida")

    processo = get_object_or_404(Processo, pk=processo_id)
    if processo.status == Processo.STATUS_FECHADO:
        return HttpResponseForbidden("Processo fechado")

    form = CandidatoAplicacaoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Formulario invalido para cadastro de candidato.")
        return redirect("processo_detail", processo_id=processo_id)

    data = form.cleaned_data
    email = data["email"].strip().lower()

    with transaction.atomic():
        candidato, _ = Candidato.objects.update_or_create(
            email=email,
            defaults={
                "nome": data["nome"],
                "linkedin": data.get("linkedin", ""),
                "greenhouse_id": data.get("greenhouse_id", ""),
                "pbix_file": data.get("pbix_file", ""),
                "optional_file": data.get("optional_file", ""),
            },
        )

        aplicacao = Aplicacao.objects.filter(candidato=candidato, processo=processo).first()
        if aplicacao:
            aplicacao.greenhouse_id = data.get("greenhouse_id", "")
            aplicacao.pbix_file = data.get("pbix_file", "")
            aplicacao.optional_file = data.get("optional_file", "")
            aplicacao.save(update_fields=["greenhouse_id", "pbix_file", "optional_file"])
            acao = "atualizado"
        else:
            Aplicacao.objects.create(
                candidato=candidato,
                processo=processo,
                greenhouse_id=data.get("greenhouse_id", ""),
                pbix_file=data.get("pbix_file", ""),
                optional_file=data.get("optional_file", ""),
            )
            acao = "adicionado"

    messages.success(request, f"Candidato {candidato.nome} {acao} no processo.")
    return redirect("processo_detail", processo_id=processo_id)


@allowed_email_required
def avaliar_aplicacao(request, aplicacao_id):
    aplicacao = get_object_or_404(Aplicacao.objects.select_related("processo", "candidato"), pk=aplicacao_id)
    if aplicacao.processo.status == Processo.STATUS_FECHADO and not _is_admin(request.user):
        return HttpResponseForbidden("Processo fechado para avaliacao")
    if not _can_edit(request.user):
        return HttpResponseForbidden("Sem permissao de edicao")

    estrutura = get_criterios_por_area(aplicacao.processo.area)
    criteria_payload = []

    for bloco_index, (bloco, criterios) in enumerate(estrutura.items()):
        for criterio_index, item in enumerate(criterios):
            criteria_payload.append(
                {
                    "bloco": bloco,
                    "criterio": item["criterio"],
                    "peso": item["peso"],
                    "field_nota": f"nota_{bloco_index}_{criterio_index}",
                    "field_just": f"just_{bloco_index}_{criterio_index}",
                }
            )

    ultima = aplicacao.avaliacoes.order_by("-data_avaliacao").first()
    existing_map = {}
    if ultima:
        existing_map = {
            (c.bloco, c.criterio): c
            for c in ultima.criterios.all()
        }

    for item in criteria_payload:
        existing = existing_map.get((item["bloco"], item["criterio"]))
        item["default_nota"] = existing.nota if existing else Decimal("5.0")
        item["default_just"] = existing.justificativa if existing else ""

    if request.method == "POST":
        comentario = request.POST.get("comentario_final", "")
        priorizacao = request.POST.get("priorizacao", "Não priorizar")
        gh_atualizada = request.POST.get("gh_atualizada") == "on"

        soma = Decimal("0")
        soma_pesos = Decimal("0")
        criterios_salvar = []

        for item in criteria_payload:
            raw = request.POST.get(item["field_nota"], "0").replace(",", ".")
            try:
                nota = Decimal(raw)
            except Exception:
                nota = Decimal("0")
            nota = max(Decimal("0"), min(Decimal("10"), nota))
            peso = Decimal(str(item["peso"]))

            soma += nota * peso
            soma_pesos += peso
            criterios_salvar.append(
                {
                    "bloco": item["bloco"],
                    "criterio": item["criterio"],
                    "nota": nota,
                    "justificativa": request.POST.get(item["field_just"], ""),
                }
            )

        nota_final = (soma / soma_pesos).quantize(Decimal("0.01")) if soma_pesos else Decimal("0")

        with transaction.atomic():
            avaliacao = aplicacao.avaliacoes.order_by("-data_avaliacao").first()
            if avaliacao:
                avaliacao.nota_final = nota_final
                avaliacao.avaliador = request.user.get_full_name() or request.user.email
                avaliacao.comentario_final = comentario
                avaliacao.priorizacao = priorizacao
                avaliacao.gh_atualizada = gh_atualizada
                avaliacao.data_avaliacao = timezone.now()
                avaliacao.save()
                avaliacao.criterios.all().delete()
            else:
                avaliacao = Avaliacao.objects.create(
                    aplicacao=aplicacao,
                    nota_final=nota_final,
                    avaliador=request.user.get_full_name() or request.user.email,
                    comentario_final=comentario,
                    priorizacao=priorizacao,
                    gh_atualizada=gh_atualizada,
                )

            AvaliacaoCriterio.objects.bulk_create(
                [
                    AvaliacaoCriterio(
                        avaliacao=avaliacao,
                        bloco=c["bloco"],
                        criterio=c["criterio"],
                        nota=c["nota"],
                        justificativa=c["justificativa"],
                    )
                    for c in criterios_salvar
                ]
            )

        messages.success(request, f"Avaliacao salva com nota final {nota_final}.")
        return redirect("processo_detail", processo_id=aplicacao.processo_id)

    context = {
        "aplicacao": aplicacao,
        "criteria_payload": criteria_payload,
        "existing_map": existing_map,
    }
    return render(request, "core/avaliar.html", context)


@allowed_email_required
def manage_emails(request):
    if not _is_admin(request.user):
        return HttpResponseForbidden("Somente admin")

    form = AllowedEmailForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.added_by = request.user.email
        obj.save()
        messages.success(request, "Email autorizado salvo com sucesso.")
        return redirect("manage_emails")

    if request.method == "POST" and "delete_email" in request.POST:
        email_id = request.POST.get("delete_email")
        AllowedEmail.objects.filter(id=email_id).delete()
        messages.success(request, "Email removido.")
        return redirect("manage_emails")

    context = {
        "form": form,
        "emails": AllowedEmail.objects.all(),
    }
    return render(request, "core/manage_emails.html", context)
