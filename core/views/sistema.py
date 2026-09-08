"""Views da area interna ("sistema"): dashboard de monitoramento e metricas,
configuracoes, gestao de qualidade, pesquisa de satisfacao, auditoria de
percurso, meu perfil, sincronizacao de agendamentos, e as ferramentas de
desenvolvimento (paineis de mock, tela generica por slug). Quarta e ultima
fatia da divisao por dominio da Fase 3 -- com ela, _legacy.py fica vazio.
"""

import csv

from django.conf import settings
from django.db import IntegrityError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from core.dev_builders import build_fake_screen_list, build_mocked_screen_payload
from core.forms import AlterarSenhaForm, MeuPerfilForm, PacientePerfilForm, UsuarioSistemaForm
from core.importer import process_appointment_file
from core.models import Agendamento, EncaixePaciente, NivelAcessoPermissao, Paciente, UsuarioSistema
from core.auth_decorators import permissao_requerida, staff_required
from core.services import (
    get_auditoria_percurso_context,
    get_dashboard_monitoramento_context,
    get_screen_context,
    list_patient_screens,
)


def _usuario_logado(request):

    """Busca o UsuarioSistema da sessao atual (ou None se nao ha ninguem
    logado) -- usado pelas telas do sistema interno pra exibir nome/cargo
    no cabecalho sem precisar repetir essa consulta em cada view."""

    uid = request.session.get("staff_usuario_id")

    return UsuarioSistema.objects.filter(pk=uid).first() if uid else None


@xframe_options_sameorigin

@staff_required

def dashboard_monitoramento_view(request):

    """Renderiza o dashboard de monitoramento com dados reais do banco."""

    from datetime import date, datetime, timedelta



    from core.models import EncaixePaciente



    hoje = date.today()

    agora = datetime.now()



    total_hoje = EncaixePaciente.objects.filter(data_atendimento=hoje).count()

    primeira_recepcao = EncaixePaciente.objects.filter(data_atendimento=hoje)[:12].count()

    pendentes = EncaixePaciente.objects.filter(data_atendimento=hoje).count()



    dias_semana = []

    for i in range(6, -1, -1):

        d = hoje - timedelta(days=i)

        count = EncaixePaciente.objects.filter(data_atendimento=d).count()

        dias_semana.append({"label": d.strftime("%a").upper()[:3], "height": count})



    usuario = _usuario_logado(request)



    context = {

        "page_title": "Monitoramento do Fluxo",

        "current_time": agora.strftime("%H:%M"),

        "current_date": agora.strftime("%d de %B de %Y").lower(),

        "system_status": "Sistema online",

        "user": {

            "initial": (usuario.nome_completo[0] if usuario else "F"),

            "name": usuario.nome_completo if usuario else "Funcionário",

            "role": usuario.get_nivel_acesso_display() if usuario else "Gestão da recepção",

        },

        "kpis": [

            {

                "title": "Check-ins recebidos",

                "value": str(total_hoje),

                "footer": "TOTAL VALIDADO",

                "is_primary": True,

                "badge_class": "green",

                "badge_text": "HOJE",

                "badge_direction": "up",

            },

            {

                "title": "Em fluxo",

                "value": str(primeira_recepcao),

                "footer": "pacientes em fluxo",

                "badge_class": "green",

                "badge_text": "ESTÁVEL",

                "badge_direction": "up",

            },

            {

                "title": "Pendências",

                "value": str(pendentes),

                "footer": "pacientes registrados",

                "badge_class": "green" if pendentes < 20 else "red",

                "badge_text": "NORMAL" if pendentes < 20 else "ALERTA",

                "badge_direction": "up",

            },

            {

                "title": "Atendimentos Concluídos",

                "value": str(EncaixePaciente.objects.filter(data_atendimento=hoje, status=EncaixePaciente.Status.CONCLUIDO).count()),

                "footer": "HOJE",

                "badge_class": "green",

                "badge_text": "CONCLUÍDO",

                "badge_direction": "up",

            },

        ],

        "chart": {

            "title": "Visão Geral do Fluxo",

            "subtitle": "Entrada de pacientes por dia (últimos 7 dias)",

            "bars": dias_semana,

        },



        "usuario_logado": usuario,

        "interno": request.GET.get("interno") == "1",

    }

    return render(request, "system/dashboard_monitoramento.html", context)


@staff_required
def dashboard_metrics_api(request):
    """Endpoint JSON usado pelos graficos do dashboard de monitoramento:
    aplica os mesmos filtros da tela (periodo, turno, tipo de atendimento)
    e devolve totais, percentuais e a serie historica dos ultimos dias."""
    from datetime import date, timedelta
    from django.db.models import Count, Avg, Q, F, DurationField, ExpressionWrapper, Value
    from django.db.models.functions import ExtractEpoch
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    shift = request.GET.get("shift", "").upper()
    service_type = request.GET.get("service_type", "").upper()
    qs = EncaixePaciente.objects.all()
    if start_date:
        qs = qs.filter(data_atendimento__gte=start_date)
    if end_date:
        qs = qs.filter(data_atendimento__lte=end_date)
    if not start_date and not end_date:
        qs = qs.filter(data_atendimento=date.today())
    if shift == "MANHA":
        qs = qs.filter(criado_em__hour__lt=12)
    elif shift == "TARDE":
        qs = qs.filter(criado_em__hour__gte=12, criado_em__hour__lt=18)
    elif shift == "NOITE":
        qs = qs.filter(criado_em__hour__gte=18)
    if service_type and service_type != "TODOS":
        qs = qs.filter(tipos_atendimento__tipo__iexact=service_type)
    total = qs.count()
    concluidos = qs.filter(status=EncaixePaciente.Status.CONCLUIDO).count()
    aguardando = qs.filter(status=EncaixePaciente.Status.AGUARDANDO).count()
    atendimento = qs.filter(status=EncaixePaciente.Status.ATENDIMENTO).count()
    absenteismo_count = qs.filter(status=EncaixePaciente.Status.CONCLUIDO, justificativa__icontains="falta").count()
    absenteismo_pct = round((absenteismo_count / total * 100) if total else 0)
    hoje = date.today()
    ref_start = start_date or (hoje - timedelta(days=6)).isoformat()
    ref_end = end_date or hoje.isoformat()
    s = date.fromisoformat(ref_start)
    e = date.fromisoformat(ref_end)
    delta = (e - s).days
    dias_semana = []
    for i in range(delta + 1):
        d = s + timedelta(days=i)
        count = EncaixePaciente.objects.filter(data_atendimento=d).count()
        dias_semana.append({"label": d.strftime("%d/%b"), "height": count})

    # TME calculation
    concluded_with_times = qs.filter(
        status=EncaixePaciente.Status.CONCLUIDO,
        chamado_em__isnull=False,
        criado_em__isnull=False,
    )
    tme_total = 0
    tme_count = 0
    tme_by_sala = {}
    for ep in concluded_with_times.only("chamado_em", "criado_em", "sala"):
        diff_min = (ep.chamado_em - ep.criado_em).total_seconds() / 60.0
        if diff_min < 0:
            diff_min = 0
        tme_total += diff_min
        tme_count += 1
        sala = ep.sala.strip() if ep.sala else "Sem sala"
        if sala not in tme_by_sala:
            tme_by_sala[sala] = {"total": 0, "count": 0}
        tme_by_sala[sala]["total"] += diff_min
        tme_by_sala[sala]["count"] += 1
    tme_average = round(tme_total / tme_count, 1) if tme_count else 0
    tme_by_reception = [
        {"name": sala, "avg": round(v["total"] / v["count"], 1)}
        for sala, v in sorted(tme_by_sala.items())
    ]

    # Absenteísmo comparison (previous period of same length)
    prev_days = max(delta, 1)
    prev_s = s - timedelta(days=prev_days + 1)
    prev_e = s - timedelta(days=1)
    prev_filter = Q(data_atendimento__gte=prev_s, data_atendimento__lte=prev_e)
    if shift:
        if shift == "MANHA":
            prev_filter &= Q(criado_em__hour__lt=12)
        elif shift == "TARDE":
            prev_filter &= Q(criado_em__hour__gte=12, criado_em__hour__lt=18)
        elif shift == "NOITE":
            prev_filter &= Q(criado_em__hour__gte=18)
    prev_qs = EncaixePaciente.objects.filter(prev_filter)
    prev_total = prev_qs.count()
    prev_abs_count = prev_qs.filter(
        status=EncaixePaciente.Status.CONCLUIDO, justificativa__icontains="falta"
    ).count()
    prev_abs_pct = round((prev_abs_count / prev_total * 100) if prev_total else 0)
    if prev_total and absenteismo_pct > prev_abs_pct:
        abs_compare = f"? {absenteismo_pct - prev_abs_pct}% em relação ao período anterior"
    elif prev_total and absenteismo_pct < prev_abs_pct:
        abs_compare = f"? {prev_abs_pct - absenteismo_pct}% em relação ao período anterior"
    elif prev_total:
        abs_compare = "Estável em relação ao período anterior"
    else:
        abs_compare = "Sem dados do período anterior"

    return JsonResponse({
        "kpis": [
            {"title": "Total de Atendimentos", "value": str(total), "footer": "PERÍODO"},
            {"title": "Tempo Médio de Espera", "value": f"{tme_average} min", "footer": "MÉDIA GERAL"},
            {"title": "Taxa de Absenteísmo", "value": f"{absenteismo_pct}%", "footer": "META <5%"},
            {"title": "Atendimentos Concluídos", "value": str(concluidos), "footer": "HOJE"},
        ],
        "chart_bars": dias_semana,
        "totals": {"total": total, "aguardando": aguardando, "atendimento": atendimento, "concluidos": concluidos},
        "filters_applied": {"start_date": start_date or "", "end_date": end_date or "", "shift": shift or "TODOS", "service_type": service_type or "TODOS"},
        "tme_average": tme_average,
        "tme_by_reception": tme_by_reception,
        "tme_reception_count": f"{len(tme_by_reception)} salas distintas",
        "absenteismo_percentage": absenteismo_pct,
        "absenteismo_compare": abs_compare,
    })


@staff_required
def qualidade_metrics_api(request):
    """Endpoint JSON com as metricas de qualidade (notas medias por
    categoria da pesquisa de satisfacao) usado pela tela de Gestao de
    Qualidade."""
    from datetime import date, timedelta
    from django.db.models import Count, Avg
    from apps.core_domain.models import PesquisaSatisfacao

    days = int(request.GET.get("days", 30))
    start_date = date.today() - timedelta(days=days)
    qs = PesquisaSatisfacao.objects.filter(criado_em__date__gte=start_date)

    total = qs.count()
    avg_nota = qs.aggregate(Avg("nota"))["nota__avg"] or 0
    avg_pct = round((avg_nota / 5) * 100)

    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for row in qs.values("nota").annotate(cnt=Count("id")):
        dist[row["nota"]] = row["cnt"]

    otimo_pct = round(((dist[4] + dist[5]) / total * 100) if total else 0)
    bom_pct = round((dist[3] / total * 100) if total else 0)
    regular_pct = round((dist[2] / total * 100) if total else 0)
    ruim_pct = round((dist[1] / total * 100) if total else 0)

    feedbacks = []
    for p in qs.filter(comentario__gt="").order_by("-criado_em")[:20]:
        nota = p.nota
        if nota >= 4:
            rotulo = "ÓTIMO"
            cor_badge = "text-emerald-600 bg-emerald-50 border-emerald-100"
        elif nota == 3:
            rotulo = "BOM"
            cor_badge = "text-blue-600 bg-blue-50 border-blue-100"
        else:
            rotulo = "RUIM"
            cor_badge = "text-red-600 bg-red-50 border-red-100"
        feedbacks.append({
            "id": p.pk,
            "nome": p.paciente_nome or "Anônimo",
            "data": p.criado_em.strftime("%d/%m/%Y, %H:%M"),
            "nota": nota,
            "comentario": p.comentario,
            "rotulo": rotulo,
            "cor_badge": cor_badge,
        })

    kpis = [
        {
            "title": "Satisfação Geral",
            "value": f"{avg_pct}%",
            "badge": "ÓTIMO" if avg_pct >= 80 else "BOM" if avg_pct >= 60 else "REGULAR" if avg_pct >= 40 else "RUIM",
            "badge_color": "emerald" if avg_pct >= 80 else "blue" if avg_pct >= 60 else "amber" if avg_pct >= 40 else "red",
            "bar_color": "bg-emerald-500" if avg_pct >= 80 else "bg-blue-600" if avg_pct >= 60 else "bg-amber-500" if avg_pct >= 40 else "bg-red-500",
        },
        {
            "title": "Total de Avaliações",
            "value": str(total),
            "badge": f"{days} dias",
            "badge_color": "slate",
            "bar_color": "bg-blue-600",
            "bar_width": min(total / 50 * 100, 100),
        },
        {
            "title": "Taxa de Respostas",
            "value": f"{otimo_pct + bom_pct}%",
            "badge": f"{otimo_pct}% ótimo",
            "badge_color": "emerald",
            "bar_color": "bg-emerald-500",
            "bar_width": otimo_pct + bom_pct,
        },
        {
            "title": "Nota Média",
            "value": f"{avg_nota:.1f}",
            "badge": f"de 5 estrelas",
            "badge_color": "blue",
            "bar_color": "bg-blue-600",
            "bar_width": avg_pct,
        },
    ]

    def _distribuicao_categoria(campo):
        """Calcula % ótimo/bom/regular/ruim para uma nota por categoria,
        ignorando registros antigos que não têm essa nota (coletados antes
        da pesquisa perguntar por atributo)."""
        sub = qs.filter(**{f"{campo}__isnull": False})
        total_cat = sub.count()
        if not total_cat:
            return {"positivo": 0, "ruim": 0, "regular": 0, "bom": 0, "otimo": 0}
        dist_cat = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for row in sub.values(campo).annotate(cnt=Count("id")):
            dist_cat[row[campo]] = row["cnt"]
        otimo_cat = round(((dist_cat[4] + dist_cat[5]) / total_cat) * 100)
        bom_cat = round((dist_cat[3] / total_cat) * 100)
        regular_cat = round((dist_cat[2] / total_cat) * 100)
        ruim_cat = round((dist_cat[1] / total_cat) * 100)
        return {"positivo": otimo_cat + bom_cat, "ruim": ruim_cat, "regular": regular_cat, "bom": bom_cat, "otimo": otimo_cat}

    atributos = [
        {"nome": "ATENDIMENTO", **_distribuicao_categoria("nota_atendimento")},
        {"nome": "ESPERA", **_distribuicao_categoria("nota_espera")},
        {"nome": "INSTALAÇÃO", **_distribuicao_categoria("nota_instalacao")},
        {"nome": "PROFISSIONAL", **_distribuicao_categoria("nota_profissional")},
        {"nome": "CLAREZA", **_distribuicao_categoria("nota_clareza")},
    ]

    alertas = []
    baixas = qs.filter(nota__lte=2).order_by("-criado_em")[:5]
    for p in baixas:
        alertas.append({
            "alerta": f"Avaliação {p.nota}?",
            "qtd": "1",
            "local": p.paciente_nome or "Anônimo",
            "status": "CRÍTICO" if p.nota == 1 else "ATENÇÃO",
            "status_color": "red" if p.nota == 1 else "amber",
        })

    return JsonResponse({
        "kpis": kpis,
        "atributos": atributos,
        "feedbacks": feedbacks,
        "alertas": alertas,
        "total": total,
        "media": round(avg_nota, 1),
        "distribuicao": dist,
    })


@xframe_options_sameorigin

def configuracoes_view(request):

    """Manage access settings and persist institutional users."""

    from apps.core_domain.permissions import usuario_tem_permissao

    usuario_id = request.session.get("staff_usuario_id")

    usuario_logado = UsuarioSistema.objects.filter(pk=usuario_id).first() if usuario_id else None

    is_admin = bool(usuario_logado and usuario_tem_permissao(usuario_logado, "usuarios"))

    tabela_vazia = not UsuarioSistema.objects.exists()

    # So deixa ver a tela se ja for staff autenticado, ou se ainda nao
    # existir nenhum usuario (bootstrap do primeiro admin).
    if not usuario_logado and not tabela_vazia:

        return redirect("login")



    form = UsuarioSistemaForm()

    edit_form = None

    edit_user = None

    if request.method == "POST":

        # Permite criar o primeiro usuário mesmo sem sessão de admin

        if not is_admin and not tabela_vazia:

            return redirect("sistema-interno")

        action = request.POST.get("action", "create")

        user_id = request.POST.get("usuario_id")



        if action == "create":

            form = UsuarioSistemaForm(request.POST)

            if form.is_valid():

                form.save()

                return _configuracoes_redirect(request, "criado")

        else:

            edit_user = get_object_or_404(UsuarioSistema, pk=user_id)

            if action == "update":

                edit_form = UsuarioSistemaForm(request.POST, instance=edit_user)

                if edit_form.is_valid():

                    edit_form.save()

                    return _configuracoes_redirect(request, "atualizado")

            elif action == "toggle":

                edit_user.usuario_ativo = not edit_user.usuario_ativo

                edit_user.save(update_fields=("usuario_ativo", "atualizado_em"))

                return _configuracoes_redirect(request, "status")

            elif action == "delete":

                edit_user.delete()

                return _configuracoes_redirect(request, "excluido")



    todos_usuarios = UsuarioSistema.objects.all()



    # Paginação: 10 usuários por página

    from django.core.paginator import Paginator

    paginator = Paginator(todos_usuarios, 10)

    pagina_atual = request.GET.get("pagina", 1)

    page_obj = paginator.get_page(pagina_atual)



    from apps.core_domain.permissions import mapa_permissoes_por_nivel

    context = {

        "usuario_form": form,

        "edit_form": edit_form,

        "edit_user": edit_user,

        "usuarios": page_obj,

        "page_obj": page_obj,

        "is_admin": is_admin,

        "pode_criar": is_admin or tabela_vazia,

        "permissoes_por_nivel": mapa_permissoes_por_nivel(),

        "pode_editar_permissoes": bool(
            usuario_logado and usuario_logado.nivel_acesso == UsuarioSistema.NivelAcesso.SUPER_ADMIN
        ),

        "salvar_permissoes_url": reverse("salvar-permissoes-nivel"),

        "usuario_logado": usuario_logado,

        "usuarios_ativos": todos_usuarios.filter(usuario_ativo=True).count(),

        "abrir_gestao_usuarios": request.GET.get("modulo") == "usuarios" or request.method == "POST",

        "resultado": request.GET.get("resultado", ""),

        "interno": request.GET.get("interno") == "1",

        "configuracoes_action_url": (

            f"{reverse('configuracoes')}?interno=1"

            if request.GET.get("interno") == "1"

            else reverse("configuracoes")

        ),

    }

    return render(request, "system/configuracoes.html", context)


def _configuracoes_redirect(request, resultado):

    """Mantém formulários de configurações dentro do painel quando abertos nele."""

    if request.GET.get("interno") == "1":

        return redirect(

            f"{reverse('sistema-interno')}?tela=configuracoes&modulo=usuarios&resultado={resultado}"

        )

    return redirect(f"{reverse('configuracoes')}?modulo=usuarios&resultado={resultado}")


@require_POST
@staff_required
def salvar_permissoes_nivel_view(request):
    """Persiste as permissões de um nível de acesso (Controle de Níveis de
    Acesso, em Configurações). Somente Super Admin pode alterar — editar a
    própria hierarquia é mais sensível que gerenciar usuários."""
    import json

    usuario = request.staff_usuario
    if usuario.nivel_acesso != UsuarioSistema.NivelAcesso.SUPER_ADMIN:
        return JsonResponse(
            {"ok": False, "erro": "Apenas Super Admin pode alterar permissões de níveis de acesso."},
            status=403,
        )

    try:
        payload = json.loads(request.body or "{}")
    except (ValueError, TypeError):
        return JsonResponse({"ok": False, "erro": "Corpo da requisição inválido."}, status=400)

    nivel_acesso = payload.get("nivel_acesso")
    permissoes = payload.get("permissoes")

    niveis_validos = {valor for valor, _ in UsuarioSistema.NivelAcesso.choices}
    permissoes_validas = {valor for valor, _ in NivelAcessoPermissao.Permissao.choices}

    if nivel_acesso not in niveis_validos or not isinstance(permissoes, dict):
        return JsonResponse({"ok": False, "erro": "Dados inválidos."}, status=400)

    for chave, ativo in permissoes.items():
        if chave not in permissoes_validas:
            continue
        NivelAcessoPermissao.objects.update_or_create(
            nivel_acesso=nivel_acesso,
            permissao=chave,
            defaults={"ativo": bool(ativo)},
        )

    return JsonResponse({"ok": True})


def health_check_view(request):

    """Endpoint simples pro serviço de deploy (Render) confirmar que a
    aplicacao esta no ar."""

    return JsonResponse({"status": "healthy"})


@xframe_options_sameorigin

def home_view(request):

    """Entrada do painel isolado, limitada aos dois fluxos do produto."""

    request.session.pop("staff_logged_in", None)

    return render(request, "display/home.html", {"title": "Painel de desenvolvimento"})


def sistema_interno_figma_view(request):

    """Shell do sistema interno com o Drawer aprovado no Figma."""

    if not request.session.get("staff_logged_in"):

        return redirect("login")

    screens = {

        "auditoria": {"label": "Atendimentos do Dia", "path": f"{reverse('screen-auditoria-percurso-seguranca')}?interno=1"},

        "monitoramento": {"label": "Dashboard", "path": f"{reverse('dashboard-monitoramento')}?interno=1"},

        "qualidade": {"label": "Gestao de Qualidade", "path": f"{reverse('gestao_qualidade')}?interno=1"},

        "configuracoes": {"label": "Configuracoes", "path": f"{reverse('configuracoes')}?interno=1"},

        "perfil": {"label": "Meu Perfil", "path": f"{reverse('meu-perfil')}?interno=1"},

        # Acesso institucional: intencionalmente fora do Drawer do Figma.

        "login": {"label": "Login", "path": f"{reverse('login')}?interno=1"},

        "cadastro": {"label": "Cadastro", "path": f"{reverse('cadastro')}?interno=1"},

    }

    active_key = request.GET.get("tela", "auditoria")

    if active_key not in screens:

        active_key = "auditoria"

    navigation_items = [

        {"key": key, **screens[key]}

        for key in ("auditoria", "monitoramento", "qualidade", "configuracoes", "perfil")

    ]

    return render(request, "system/sistema_interno.html", {

        "navigation_items": navigation_items,

        "active_key": active_key,

        "active_screen": screens[active_key],

    })


def screen_view(request, screen_slug):

    """Thin view: only render context produced by the application service."""

    context = get_screen_context(screen_slug)

    if context is None:

        raise Http404("Tela não encontrada")

    return render(request, "core/screen.html", context)


@xframe_options_sameorigin

@permissao_requerida("auditoria")

def auditoria_percurso_seguranca_view(request):

    """Thin view for the audit screen, keeping business data in services."""

    from datetime import date



    hoje = date.today()



    resultado_import = None

    if request.method == "POST":

        arquivo = request.FILES.get("arquivo_import")

        if arquivo:

            data_post_str = request.POST.get("data_alvo", "")

            data_post = hoje

            if data_post_str:

                try:

                    data_post = date.fromisoformat(data_post_str)

                except ValueError:

                    pass

            resultado_import = process_appointment_file(arquivo, target_date=data_post)



    filtros = {

        "q": request.GET.get("q", ""),

        "data": request.GET.get("data", ""),

        "data_inicio": request.GET.get("data_inicio", ""),

        "data_fim": request.GET.get("data_fim", ""),

        "setor": request.GET.get("setor", ""),

        "status": request.GET.get("status", ""),

        "apenas_alertas": request.GET.get("apenas_alertas", ""),

    }



    context = get_auditoria_percurso_context(filtros)

    context["interno"] = request.GET.get("interno") == "1"

    context["usuario_logado"] = _usuario_logado(request)



    context["total_agendamentos"] = Agendamento.objects.filter(data_agendamento=hoje).count()

    context["aguardando_checkin"] = Agendamento.objects.filter(

        data_agendamento=hoje, status=Agendamento.Status.AGENDADO

    ).count()

    context["checkin_realizado"] = Agendamento.objects.filter(

        data_agendamento=hoje, status=Agendamento.Status.CHECKIN_REALIZADO

    ).count()

    context["resultado_import"] = resultado_import

    from core.models import EncaixePaciente
    STATUS_DISPLAY = {
        EncaixePaciente.Status.VALIDACAO: "EM VALIDAÇÃO",
        EncaixePaciente.Status.AGUARDANDO: "AGUARDANDO",
        EncaixePaciente.Status.CHAMADO: "CHAMADO",
        EncaixePaciente.Status.ATENDIMENTO: "EM ATENDIMENTO",
        EncaixePaciente.Status.CONCLUIDO: "FINALIZADO",
    }
    context["STATUS_DISPLAY"] = STATUS_DISPLAY

    KANBAN_COLUMNS = [
        (EncaixePaciente.Status.VALIDACAO, "EM VALIDAÇÃO", "wait"),
        (EncaixePaciente.Status.AGUARDANDO, "AGUARDANDO", "wait"),
        (EncaixePaciente.Status.CHAMADO, "CHAMADO", "ok"),
        (EncaixePaciente.Status.ATENDIMENTO, "EM ATENDIMENTO", "ok"),
        (EncaixePaciente.Status.CONCLUIDO, "FINALIZADO", "ok"),
    ]

    kanban_columns = []
    for status_val, title, color in KANBAN_COLUMNS:
        pts = [p for p in context["pacientes"] if p.get("status_raw") == status_val]
        kanban_columns.append({
            "title": title,
            "color": color,
            "count": len(pts),
            "patients": pts,
            "footer_text": f"{len(pts)} paciente(s)",
        })
    context["kanban_columns"] = kanban_columns


    if request.GET.get("export") == "csv":

        response = HttpResponse(content_type="text/csv")

        response["Content-Disposition"] = 'attachment; filename="auditoria_percurso_seguranca.csv"'



        writer = csv.writer(response)

        writer.writerow(

            [

                "Ordem",

                "Ficha",

                "Paciente",

                "CPF",

                "Check-in",

                "Entrada Fila",

                "Chamada",

                "Encerramento",

                "Status",

                "Setor",

                "Data Referência",

                "Badges",

                "Log",

            ]

        )



        for paciente in context["pacientes"]:

            writer.writerow(

                [

                    paciente.get("ordem", ""),

                    paciente.get("ficha", ""),

                    paciente.get("nome", ""),

                    paciente.get("cpf", ""),

                    paciente.get("check_in", ""),

                    paciente.get("entrada_fila", ""),

                    paciente.get("chamada", ""),

                    paciente.get("encerramento", ""),

                    paciente.get("status", ""),

                    paciente.get("setor", ""),

                    paciente.get("data_referencia", ""),

                    " | ".join(paciente.get("badges", [])),

                    paciente.get("log", ""),

                ]

            )

        return response



    return render(request, "system/auditoria_percurso_seguranca.html", context)


def dev_mock_list_view(request):

    """Hidden route for isolated front-end work with generated fake cards."""

    if not settings.DEBUG:

        raise Http404("Not found")



    qty = int(request.GET.get("qty", "6"))

    context = {

        "title": "Painel de Desenvolvimento Isolado",

        "mobile_group": {

            "title": "Telas Mobile",

            "path": reverse("painel-pacientes"),

            "count": len(list_patient_screens()),

            "desc": "Telas do fluxo do paciente (identificação, check-in, fila, chamada, etc.)",

        },

        "tv_group": {

            "title": "Painel de Chamada",

            "path": reverse("painel-chamada"),

            "desc": "Painel TV em tempo real com WebSocket e áudio",

        },

        "system_group": {

            "title": "Sistema Interno",

            "path": reverse("login"),

            "desc": "Área institucional: colaboradores, gerência e SuperAdmin",

        },

        "fake_cards": build_fake_screen_list(quantity=max(1, min(qty, 20))),

    }

    return render(request, "core/dev_preview.html", context)


def dev_mock_screen_view(request, screen_slug):

    """Hidden route to render one mocked screen without full DB setup."""

    if not settings.DEBUG:

        raise Http404("Not found")



    use_factory = request.GET.get("factory", "0") == "1"

    context = build_mocked_screen_payload(screen_slug=screen_slug, use_factory=use_factory)

    return render(request, "core/screen.html", context)


@xframe_options_sameorigin

@staff_required

def gestao_qualidade_view(request):

    """Tela de Gestao de Qualidade -- so renderiza o shell; os numeros em
    si vem via qualidade_metrics_api, consumido pelo JS da pagina."""

    return render(request, 'system/gestao_qualidade.html', {

        "interno": request.GET.get("interno") == "1",

        "usuario_logado": _usuario_logado(request),

    })


@xframe_options_sameorigin

def pesquisa_satisfacao_view(request):

    """Tela de pesquisa de satisfacao mostrada ao paciente logo apos a
    conclusao do atendimento (ver concluir_atendimento_view, que monta o
    redirect_url pra cá com o CPF). Se o CPF vier na URL, busca o nome do
    paciente so pra personalizar a saudacao -- a resposta em si e
    anonima/por CPF, nao exige login."""

    cpf = request.GET.get("cpf", "")

    paciente_nome = ""

    if cpf:

        from apps.core_domain.models import EncaixePaciente

        encaixe = EncaixePaciente.objects.filter(

            cpf=cpf,

        ).order_by("-criado_em").first()

        if encaixe:

            paciente_nome = encaixe.nome_completo

    return render(request, 'mobile/pesquisa_satisfacao.html', {

        "cpf": cpf,

        "paciente_nome": paciente_nome,

    })


@xframe_options_sameorigin

def meu_perfil_view(request):

    """Tela "Meu Perfil", compartilhada entre paciente e staff logados --
    edita dados basicos e troca de senha. As funcoes internas abaixo
    resolvem qual das duas sessoes (paciente ou staff) esta ativa e
    montam um contexto no mesmo formato pra ambos os casos."""

    def _iniciais(nome):

        partes = (nome or "").split()

        return "".join(p[0] for p in partes[:2]).upper() or "?"



    def _ctx(interno, usuario, paciente, form, extra=None):

        # Prioridade: paciente > usuario (mesma regra usada para escolher a
        # instância exibida). O papel exibido precisa ser derivado da MESMA
        # instância, senão uma sessão com paciente e funcionário coexistindo
        # (ex.: navegador reaproveitado entre login interno e check-in mobile)
        # mostra nome/CPF do paciente junto com o cargo do funcionário.
        instancia = paciente or usuario

        nome = instancia.nome_completo if instancia else "Sem vínculo"

        if instancia is not None and instancia is paciente:
            papel = "Paciente"
        elif instancia is not None and instancia is usuario:
            papel = usuario.get_nivel_acesso_display()
        else:
            papel = "Paciente"

        ctx = {

            "interno": interno,

            "usuario": usuario,

            "paciente": paciente,

            "form": form,

            "cpf_perfil": instancia.cpf if instancia else "",

            "nome_perfil": nome,

            "iniciais_perfil": _iniciais(nome),

            "papel_perfil": papel,

            "senha_form": AlterarSenhaForm(),

        }

        if extra:

            ctx.update(extra)

        return ctx



    interno = request.GET.get("interno") == "1"



    if not request.session.get("staff_logged_in") and not request.session.get("paciente_id"):

        return render(request, "core/meu_perfil.html", _ctx(

            interno, None, None, MeuPerfilForm(),

            {"erro": "Sessão expirada. Faça login novamente."}

        ))



    paciente_id = request.session.get("paciente_id")

    usuario_id = request.session.get("staff_usuario_id")

    paciente = Paciente.objects.filter(pk=paciente_id, paciente_ativo=True).first() if paciente_id else None

    usuario = UsuarioSistema.objects.filter(pk=usuario_id).first() if usuario_id else None



    FormClass = PacientePerfilForm if paciente else MeuPerfilForm

    instancia = paciente if paciente else usuario

    form = FormClass(instance=instancia) if instancia else FormClass()

    if request.method == "POST":

        if instancia is None:

            return render(request, "core/meu_perfil.html", _ctx(

                interno, None, None, FormClass(),

                {"erro": "Usuário não vinculado à sessão. Faça login novamente."}

            ))

        action = request.POST.get("action", "atualizar_perfil")

        if action == "trocar_senha":

            senha_form = AlterarSenhaForm(request.POST, instancia=instancia)

            if senha_form.is_valid():

                instancia.set_senha(senha_form.cleaned_data["nova_senha"])

                instancia.save(update_fields=["senha_hash", "atualizado_em"])

                return render(request, "core/meu_perfil.html", _ctx(

                    interno, usuario, paciente, form, {"senha_sucesso": True}

                ))

            return render(request, "core/meu_perfil.html", _ctx(

                interno, usuario, paciente, form,

                {"senha_form": senha_form, "abrir_modal_senha": True}

            ))

        form = FormClass(request.POST, instance=instancia)

        if form.is_valid():

            try:

                form.save()

                return render(request, "core/meu_perfil.html", _ctx(

                    interno, usuario, paciente, form, {"sucesso": True}

                ))

            except IntegrityError:

                form.add_error(None, "Erro ao salvar: dado já em uso por outro cadastro.")

    return render(request, "core/meu_perfil.html", _ctx(interno, usuario, paciente, form))


@staff_required
def dashboard_metrics_export(request):
    """Gera um CSV pra download com os mesmos filtros e dados do dashboard
    de monitoramento -- pensado pra alguem levar os numeros pra fora do
    sistema (planilha, relatorio)."""
    import csv
    from datetime import date, timedelta

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    shift = request.GET.get("shift", "").upper()
    service_type = request.GET.get("service_type", "").upper()

    qs = EncaixePaciente.objects.all()

    if start_date:
        qs = qs.filter(data_atendimento__gte=start_date)
    if end_date:
        qs = qs.filter(data_atendimento__lte=end_date)
    if not start_date and not end_date:
        qs = qs.filter(data_atendimento=date.today())

    if shift == "MANHA":
        qs = qs.filter(criado_em__hour__lt=12)
    elif shift == "TARDE":
        qs = qs.filter(criado_em__hour__gte=12, criado_em__hour__lt=18)
    elif shift == "NOITE":
        qs = qs.filter(criado_em__hour__gte=18)

    if service_type and service_type != "TODOS":
        qs = qs.filter(tipos_atendimento__tipo__iexact=service_type)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="dashboard_metrics.csv"'
    writer = csv.writer(response)
    writer.writerow(["Senha", "Paciente", "CPF", "Data", "Status", "Sala", "Criado em", "Chamado em"])
    for e in qs.iterator():
        writer.writerow([
            e.senha,
            e.nome_completo,
            e.cpf,
            e.data_atendimento,
            e.status,
            e.sala,
            e.criado_em.strftime("%d/%m/%Y %H:%M") if e.criado_em else "",
            e.chamado_em.strftime("%d/%m/%Y %H:%M") if e.chamado_em else "",
        ])
    return response


@staff_required

@require_POST

def sincronizar_agendamentos_view(request):

    """Aciona manualmente a sincronizacao de agendamentos do dia
    (core.integrador.sincronizar_agendamentos) a partir da tela -- mesma
    logica usada pelo comando de management, so que disparada por um
    clique em vez de agendada."""

    from datetime import date
    from core.integrador import sincronizar_agendamentos

    data_str = request.POST.get("data", "")
    data_alvo = date.fromisoformat(data_str) if data_str else None
    resultado = sincronizar_agendamentos(data_alvo=data_alvo)
    return JsonResponse(resultado)
