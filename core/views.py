import csv

import json



from django.conf import settings

from django.db import IntegrityError

from django.http import Http404, HttpResponse, JsonResponse

from django.shortcuts import get_object_or_404, redirect, render

from django.urls import reverse

from django.views.decorators.clickjacking import xframe_options_sameorigin

from django.views.decorators.http import require_http_methods, require_POST



from core.dev_builders import build_fake_screen_list, build_mocked_screen_payload

from core.forms import CadastroPacienteForm, EncaixeForm, IdentificacaoForm, LoginPacienteForm, MeuPerfilForm, PacientePerfilForm, UsuarioSistemaForm

from core.importer import process_appointment_file

from core.models import Agendamento, EncaixePaciente, Paciente, UsuarioSistema

from core.websocket_utils import notificar_fila_atualizada, notificar_paciente
from core.auth_decorators import staff_required

from core.services import (

    _get_painel_chamada_asset_data_url,

    get_acompanhamento_atendimento_context,

    get_auditoria_percurso_context,

    get_bloqueio_direcionamento_context,

    get_cadastro_context,

    get_checkin_assistido_context,

    get_checkin_concluido_context,

    get_dashboard_monitoramento_context,

    get_identificacao_paciente_context,

    get_login_context,

    get_painel_chamada_context,

    get_paciente_chamado_context,

    get_screen_context,

    list_patient_screens,

    registrar_checkin,

    registrar_encaixe,

)





def _usuario_logado(request):

    uid = request.session.get("staff_usuario_id")

    return UsuarioSistema.objects.filter(pk=uid).first() if uid else None





@xframe_options_sameorigin

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

def dashboard_metrics_api(request):
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
        abs_compare = f"↑ {absenteismo_pct - prev_abs_pct}% em relação ao período anterior"
    elif prev_total and absenteismo_pct < prev_abs_pct:
        abs_compare = f"↓ {prev_abs_pct - absenteismo_pct}% em relação ao período anterior"
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


def qualidade_metrics_api(request):
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

    atributos = [
        {"nome": "ATENDIMENTO", "positivo": otimo_pct + bom_pct, "ruim": ruim_pct, "regular": regular_pct, "bom": bom_pct, "otimo": otimo_pct},
        {"nome": "ESPERA", "positivo": otimo_pct + bom_pct, "ruim": ruim_pct, "regular": regular_pct, "bom": bom_pct, "otimo": otimo_pct},
        {"nome": "INSTALAÇÃO", "positivo": otimo_pct + bom_pct, "ruim": ruim_pct, "regular": regular_pct, "bom": bom_pct, "otimo": otimo_pct},
        {"nome": "PROFISSIONAL", "positivo": otimo_pct + bom_pct, "ruim": ruim_pct, "regular": regular_pct, "bom": bom_pct, "otimo": otimo_pct},
        {"nome": "CLAREZA", "positivo": otimo_pct + bom_pct, "ruim": ruim_pct, "regular": regular_pct, "bom": bom_pct, "otimo": otimo_pct},
    ]

    alertas = []
    baixas = qs.filter(nota__lte=2).order_by("-criado_em")[:5]
    for p in baixas:
        alertas.append({
            "alerta": f"Avaliação {p.nota}★",
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

def painel_chamada_view(request):

    context = get_painel_chamada_context(use_real_data=True)

    return render(request, "display/painel_chamada.html", context)





@xframe_options_sameorigin

def paciente_chamado_view(request):

    encaixe_id = request.session.get("encaixe_id")

    encaixe = None

    if encaixe_id:

        encaixe = EncaixePaciente.objects.filter(pk=encaixe_id).first()

    if not encaixe:

        paciente_id = request.session.get("paciente_id")

        if paciente_id:

            paciente = Paciente.objects.filter(pk=paciente_id).first()

            if paciente:

                encaixe = EncaixePaciente.objects.filter(cpf=paciente.cpf).order_by("-criado_em").first()

    if encaixe:

        if encaixe.status not in (
            EncaixePaciente.Status.CHAMADO,
            EncaixePaciente.Status.ATENDIMENTO,
        ):
            return redirect("acompanhamento-atendimento")

        tipos = list(encaixe.tipos_atendimento.all())

        context = {

            "page_title": "Paciente Chamado",

            "title": "PACIENTE CHAMADO",

            "subtitle": "Dirija-se ao local indicado para atendimento",

            "senha": encaixe.senha,

            "paciente": encaixe.nome_completo,

            "sala": encaixe.sala or "10",

            "cpf": encaixe.cpf,

            "tipo_atendimento": tipos[0].get_tipo_display() if tipos else "Ambulatorial",

            "status": "Chamada atual",

            "mensagem": "Se precisar de ajuda, procure a recepção.",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

            "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),

        }

        return render(request, "mobile/paciente_chamado.html", context)

    return render(request, "mobile/paciente_chamado.html", get_paciente_chamado_context())





@xframe_options_sameorigin

def acompanhamento_atendimento_view(request):

    encaixe_id = request.session.get("encaixe_id")

    encaixe = None

    if encaixe_id:

        encaixe = EncaixePaciente.objects.filter(pk=encaixe_id).first()

    if not encaixe:

        paciente_id = request.session.get("paciente_id")

        if paciente_id:

            paciente = Paciente.objects.filter(pk=paciente_id).first()

            if paciente:

                encaixe = EncaixePaciente.objects.filter(cpf=paciente.cpf).order_by("-criado_em").first()

    if encaixe:

        pacientes_a_frente = EncaixePaciente.objects.filter(

            data_atendimento=encaixe.data_atendimento,

            status=EncaixePaciente.Status.AGUARDANDO,

            posicao_fila__lt=encaixe.posicao_fila,

        ).count()

        chamando_agora = EncaixePaciente.objects.filter(

            data_atendimento=encaixe.data_atendimento,

            status__in=[EncaixePaciente.Status.CHAMADO, EncaixePaciente.Status.ATENDIMENTO],

        ).order_by("-chamado_em").first()

        tipos = list(encaixe.tipos_atendimento.all())

        context = {

            "page_title": "Acompanhamento de Atendimento",

            "title_line_1": "Acompanhamento de",

            "title_line_2": "Atendimento",

            "subtitle": "Confira sua posição atual na fila",

            "paciente": encaixe.nome_completo,

            "senha": encaixe.senha,

            "cpf": encaixe.cpf,

            "sala_prevista": encaixe.sala or "Sala 1",

            "tipo_atendimento": tipos[0].get_tipo_display() if tipos else "Ambulatorial",

            "chamando_agora": chamando_agora.senha if chamando_agora else "---",

            "pacientes_a_frente": pacientes_a_frente,

            "mensagem": "Permaneça atento ao painel de chamadas e aguarde sua vez.",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

            "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),

        }

        return render(request, "mobile/acompanhamento_atendimento.html", context)

    return render(request, "mobile/acompanhamento_atendimento.html", get_acompanhamento_atendimento_context())





@xframe_options_sameorigin

def checkin_concluido_view(request):

    encaixe_id = request.session.get("encaixe_id")

    encaixe = None

    if encaixe_id:

        encaixe = EncaixePaciente.objects.filter(pk=encaixe_id).first()

    if not encaixe:

        paciente_id = request.session.get("paciente_id")

        if paciente_id:

            paciente = Paciente.objects.filter(pk=paciente_id).first()

            if paciente:

                encaixe = EncaixePaciente.objects.filter(cpf=paciente.cpf).order_by("-criado_em").first()

    if encaixe:

        context = {

            "page_title": "Check-in concluído",

            "title": "Check-in concluído",

            "subtitle": "Você já está na fila de atendimento",

            "paciente": encaixe.nome_completo,

            "senha": encaixe.senha,

            "mensagem": "Acompanhe sua posição na fila e aguarde sua chamada.",

            "texto_botao": "Acompanhar fila",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

            "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),

        }

        return render(request, "mobile/checkin_concluido.html", context)

    return render(request, "mobile/checkin_concluido.html", get_checkin_concluido_context())





@xframe_options_sameorigin

def checkin_assistido_view(request):

    return render(

        request,

        "mobile/checkin_assistido.html",

        get_checkin_assistido_context(),

    )





@xframe_options_sameorigin

def bloqueio_direcionamento_view(request):

    return render(

        request,

        "mobile/bloqueio_direcionamento.html",

        get_bloqueio_direcionamento_context(),

    )





@xframe_options_sameorigin

def identificacao_paciente_view(request):

    if request.method == "POST":

        form = IdentificacaoForm(request.POST)

        if form.is_valid():

            cpf = form.cleaned_data["cpf"]

            data_nasc = form.cleaned_data.get("data_nascimento")

            nome_mae = form.cleaned_data.get("nome_mae", "")



            paciente = Paciente.objects.filter(cpf=cpf, paciente_ativo=True).first()

            if not paciente:

                return redirect("agendamento_nao_encontrado")



            encaixe = registrar_checkin(paciente, data_nasc, nome_mae)

            if not encaixe:

                return redirect("agendamento_nao_encontrado")



            request.session["encaixe_id"] = encaixe.pk

            request.session["paciente_id"] = paciente.pk

            return redirect("checkin-concluido")



        context = {**get_identificacao_paciente_context(), "form": form}

        return render(request, "mobile/identificacao_paciente.html", context)

    context = {**get_identificacao_paciente_context(), "form": IdentificacaoForm()}

    return render(request, "mobile/identificacao_paciente.html", context)





@xframe_options_sameorigin

def configuracoes_view(request):

    """Manage access settings and persist institutional users."""

    usuario_id = request.session.get("staff_usuario_id")

    usuario_logado = UsuarioSistema.objects.filter(pk=usuario_id).first() if usuario_id else None

    is_admin = usuario_logado and usuario_logado.nivel_acesso == UsuarioSistema.NivelAcesso.SUPER_ADMIN

    tabela_vazia = not UsuarioSistema.objects.exists()



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



    context = {

        "usuario_form": form,

        "edit_form": edit_form,

        "edit_user": edit_user,

        "usuarios": page_obj,

        "page_obj": page_obj,

        "is_admin": is_admin,

        "pode_criar": is_admin or tabela_vazia,

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





def fluxo_paciente_view(request):

    from datetime import date, datetime, timedelta



    dias_pt = ["SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA", "SEXTA-FEIRA", "SÁBADO", "DOMINGO"]

    meses_pt = ["", "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]



    step = request.GET.get("step", "identificacao")

    context = {

        "step": step,

        "page_title": "Fluxo do Paciente",

        "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),

        "cer_logo_url": _get_painel_chamada_asset_data_url("logo-cer.svg"),

    }



    if step == "identificacao":

        context.update({

            "page_title": "Identificação do Paciente",

            "title": "Bem-vindo",

            "subtitle": "Digite seus dados para iniciar o atendimento",

            "texto_botao_principal": "Realizar Check-in",

            "texto_botao_assistido": "Preciso de Ajuda",

            "validation_title": "Verificando seus dados",

            "validation_detail": "Conexão protegida",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

        })

        if request.method == "POST":

            form = IdentificacaoForm(request.POST)

            if form.is_valid():

                cpf = form.cleaned_data["cpf"]

                data_nasc = form.cleaned_data.get("data_nascimento")

                nome_mae = form.cleaned_data.get("nome_mae", "")



                if cpf == "00000000000":

                    return redirect(f"{reverse('fluxo-paciente')}?step=bloqueio")



                paciente = Paciente.objects.filter(cpf=cpf, paciente_ativo=True).first()

                if not paciente:

                    return redirect(f"{reverse('fluxo-paciente')}?step=agendamento-nao-encontrado")



                if data_nasc and paciente.data_nascimento and data_nasc != paciente.data_nascimento:

                    return redirect(f"{reverse('fluxo-paciente')}?step=agendamento-nao-encontrado")



                encaixe_ativo = EncaixePaciente.objects.filter(
                    cpf=cpf,
                    data_atendimento=timezone.localdate(),
                ).exclude(
                    status=EncaixePaciente.Status.CONCLUIDO,
                ).order_by("-criado_em").first()

                if encaixe_ativo:
                    step_map = {
                        EncaixePaciente.Status.AGUARDANDO: "acompanhamento",
                        EncaixePaciente.Status.CHAMADO: "paciente-chamado",
                        EncaixePaciente.Status.ATENDIMENTO: "paciente-chamado",
                        EncaixePaciente.Status.AUSENTE: "perdeu-chamada",
                    }
                    request.session["encaixe_id"] = encaixe_ativo.pk
                    request.session["paciente_id"] = paciente.pk
                    return redirect(
                        f"{reverse('fluxo-paciente')}?step={step_map.get(encaixe_ativo.status, 'acompanhamento')}"
                    )

                encaixe = registrar_checkin(paciente, data_nasc, nome_mae)

                if not encaixe:

                    return redirect(f"{reverse('fluxo-paciente')}?step=agendamento-nao-encontrado")



                request.session["encaixe_id"] = encaixe.pk

                request.session["paciente_id"] = paciente.pk

                return redirect(f"{reverse('fluxo-paciente')}?step=checkin-concluido")

            context["form"] = form

            return render(request, "mobile/fluxo_paciente.html", context)

        context["form"] = IdentificacaoForm()

        return render(request, "mobile/fluxo_paciente.html", context)



    if step == "checkin-assistido":

        context.update({

            "page_title": "Check-in Assistido",

            "title": "Siga para a Recepção",

            "message": "Nossa equipe no balcão principal ajudará com seu check-in. Por favor, tenha um documento com foto em mãos.",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

        })

        return render(request, "mobile/fluxo_paciente.html", context)



    if step == "bloqueio":

        context.update({

            "page_title": "Bloqueio e Direcionamento",

            "title_line_1": "Confirmação presencial",

            "title_line_2": "necessária",

            "subtitle": "Seus dados foram encontrados, mas seu atendimento precisa de confirmação presencial.",

            "next_step_label": "PRÓXIMO PASSO",

            "next_step_title": "Dirija-se à recepção",

            "next_step_description": "A equipe confirmará seus dados e orientará os próximos passos.",

            "location_label": "Local",

            "location": "Balcão da recepção",

            "info_message": "Seu atendimento continuará após a confirmação na recepção.",

            "status": "Confirmação na recepção",

            "review_label": "Revisar meus dados",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

        })

        return render(request, "mobile/fluxo_paciente.html", context)



    if step == "agendamento-nao-encontrado":

        return render(request, "mobile/fluxo_paciente.html", context)



    encaixe_id = request.session.get("encaixe_id")

    encaixe = None

    if encaixe_id:

        encaixe = EncaixePaciente.objects.filter(pk=encaixe_id).first()

    if not encaixe:

        paciente_id = request.session.get("paciente_id")

        if paciente_id:

            paciente = Paciente.objects.filter(pk=paciente_id).first()

            if paciente:

                encaixe = EncaixePaciente.objects.filter(cpf=paciente.cpf).order_by("-criado_em").first()



    if step == "checkin-concluido" and encaixe:

        context.update({

            "page_title": "Check-in concluído",

            "title": "Check-in concluído",

            "subtitle": "Você já está na fila de atendimento",

            "paciente": encaixe.nome_completo,

            "senha": encaixe.senha,

            "mensagem": "Acompanhe sua posição na fila e aguarde sua chamada.",

            "texto_botao": "Acompanhar fila",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

        })

        return render(request, "mobile/fluxo_paciente.html", context)



    if step == "acompanhamento" and encaixe:

        pacientes_a_frente = EncaixePaciente.objects.filter(

            data_atendimento=encaixe.data_atendimento,

            status=EncaixePaciente.Status.AGUARDANDO,

            posicao_fila__lt=encaixe.posicao_fila,

        ).count()

        chamando_agora = EncaixePaciente.objects.filter(

            data_atendimento=encaixe.data_atendimento,

            status__in=[EncaixePaciente.Status.CHAMADO, EncaixePaciente.Status.ATENDIMENTO],

        ).order_by("-chamado_em").first()

        tipos = list(encaixe.tipos_atendimento.all())

        context.update({

            "page_title": "Acompanhamento de Atendimento",

            "title_line_1": "Acompanhamento de",

            "title_line_2": "Atendimento",

            "subtitle": "Confira sua posição atual na fila",

            "paciente": encaixe.nome_completo,

            "senha": encaixe.senha,

            "cpf": encaixe.cpf,

            "sala_prevista": encaixe.sala or "Sala 1",

            "tipo_atendimento": tipos[0].get_tipo_display() if tipos else "Ambulatorial",

            "chamando_agora": chamando_agora.senha if chamando_agora else "---",

            "pacientes_a_frente": pacientes_a_frente,

            "mensagem": "Permaneça atento ao painel de chamadas e aguarde sua vez.",

            "fo_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

        })

        return render(request, "mobile/fluxo_paciente.html", context)



    if step == "paciente-chamado" and encaixe:

        tipos = list(encaixe.tipos_atendimento.all())

        context.update({

            "page_title": "Paciente Chamado",

            "title": "PACIENTE CHAMADO",

            "subtitle": "Dirija-se ao local indicado para atendimento",

            "senha": encaixe.senha,

            "paciente": encaixe.nome_completo,

            "sala": encaixe.sala or "10",

            "cpf": encaixe.cpf,

            "tipo_atendimento": tipos[0].get_tipo_display() if tipos else "Ambulatorial",

            "status": "Chamada atual",

            "mensagem": "Se precisar de ajuda, procure a recepção.",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

        })

        return render(request, "mobile/fluxo_paciente.html", context)



    if step == "perdeu-chamada" and encaixe:

        context.update({

            "page_title": "Senha Perdida",

            "atendimento": {

                "senha": encaixe.senha,

                "setor": "Recepção Central",

                "horario_chamada": encaixe.chamado_em.strftime("%H:%M") if encaixe.chamado_em else "--:--",

            },

        })

        return render(request, "mobile/fluxo_paciente.html", context)



    if step in ("checkin-concluido", "acompanhamento", "paciente-chamado", "perdeu-chamada") and not encaixe:

        return redirect(f"{reverse('fluxo-paciente')}?step=identificacao")



    return redirect(f"{reverse('fluxo-paciente')}?step=identificacao")





def perdeu_chamada_view(request, **kwargs):

    """Renderiza a tela de aviso de senha perdida para o paciente."""

    encaixe_id = request.session.get("encaixe_id")

    encaixe = None

    if encaixe_id:

        encaixe = EncaixePaciente.objects.filter(pk=encaixe_id).first()

    if not encaixe:

        paciente_id = request.session.get("paciente_id")

        if paciente_id:

            paciente = Paciente.objects.filter(pk=paciente_id).first()

            if paciente:

                encaixe = EncaixePaciente.objects.filter(cpf=paciente.cpf).order_by("-criado_em").first()

    if encaixe:

        context = {

            "page_title": "Senha Perdida",

            "atendimento": {

                "senha": encaixe.senha,

                "setor": "Recepção Central",

                "horario_chamada": encaixe.criado_em.strftime("%H:%M") if encaixe.criado_em else "--:--",

            }

        }

        return render(request, "mobile/perdeu_chamada.html", context)

    return render(request, "mobile/perdeu_chamada.html", {

        "page_title": "Senha Perdida",

        "atendimento": {

            "senha": "---",

            "setor": "Recepção Central",

            "horario_chamada": "--:--",

        }

    })





@require_http_methods(["GET"])

def paciente_status_api_view(request):

    cpf = request.GET.get("cpf", "").strip()

    if not cpf:

        return JsonResponse({"erro": "CPF obrigat\u00f3rio"}, status=400)

    encaixe = EncaixePaciente.objects.filter(cpf=cpf).order_by("-criado_em").first()

    if not encaixe:

        return JsonResponse({"erro": "Paciente n\u00e3o encontrado"}, status=404)

    return JsonResponse({

        "status": encaixe.status,

        "senha": encaixe.senha,

        "sala": encaixe.sala,

        "nome": encaixe.nome_completo,

    })





@xframe_options_sameorigin

def home_view(request):

    """Entrada do painel isolado, limitada aos dois fluxos do produto."""

    request.session.pop("staff_logged_in", None)

    return render(request, "display/home.html", {"title": "Painel de desenvolvimento"})





@xframe_options_sameorigin

def painel_pacientes_view(request):

    """Lista isolada das telas mobile destinadas ao usuário final."""

    return render(

        request,

        "mobile/painel_pacientes.html",

        {"screens": list_patient_screens()},

    )





def sistema_interno_view(request):

    """Shell único do sistema interno; a tela é escolhida pelo parâmetro ``tela``."""

    screens = {

        "monitoramento": {"label": "Monitoramento do fluxo", "path": f"{reverse('dashboard-monitoramento')}?interno=1"},

        "perfil": {"label": "Meu perfil", "path": f"{reverse('meu-perfil')}?interno=1"},

        "triagem": {"label": "Triagem", "path": None},

        "chamadas": {"label": "Chamadas", "path": None},

        "presenca": {"label": "Controle de presença", "path": None},

        "qualidade": {"label": "Gestão da qualidade", "path": f"{reverse('gestao_qualidade')}?interno=1"},

        "auditoria": {"label": "Auditoria e segurança", "path": f"{reverse('screen-auditoria-percurso-seguranca')}?interno=1"},

        "configuracoes": {"label": "Configurações", "path": f"{reverse('configuracoes')}?interno=1"},

        "login": {"label": "Login", "path": f"{reverse('login')}?interno=1"},

        "cadastro": {"label": "Cadastro", "path": f"{reverse('cadastro')}?interno=1"},

    }

    def items(*keys):

        return [{"key": key, **screens[key]} for key in keys]



    navigation_groups = [

        {"role": "Colaboradores", "screens": items("monitoramento", "perfil", "triagem", "chamadas", "presenca")},

        {"role": "Gerência", "screens": items("qualidade", "auditoria")},

        {"role": "SuperAdmin", "screens": items("configuracoes")},

        {"role": "Acesso ao sistema", "screens": items("login", "cadastro")},

    ]

    active_key = request.GET.get("tela", "monitoramento")

    if active_key not in screens:

        active_key = "monitoramento"

    return render(request, "system/sistema_interno.html", {

        "navigation_groups": navigation_groups,

        "active_key": active_key,

        "active_screen": screens[active_key],

    })





@xframe_options_sameorigin

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



@xframe_options_sameorigin

def checagem_documentos_view(request):

    """Renderiza a tela de checagem de documentos"""

    encaixe_id = request.GET.get("encaixe_id") or request.session.get("encaixe_id")
    cpf = request.GET.get("cpf", "").strip()

    encaixe = None
    if encaixe_id:
        encaixe = EncaixePaciente.objects.filter(pk=encaixe_id).first()
    if not encaixe and cpf:
        encaixe = EncaixePaciente.objects.filter(cpf=cpf).order_by("-criado_em").first()

    context = {
        "page_title": "Checagem de Documentos",
        "title": "Checagem de Documentos",
        "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),
        "footer_indicators": [
            {"label": "LGPD", "detail": "Conforme", "icon": "lock"},
            {"label": "Conexão", "detail": "Segura", "icon": "shield"},
        ],
    }

    if encaixe:
        tipos = list(encaixe.tipos_atendimento.all())
        context["paciente_nome"] = encaixe.nome_completo
        context["exame_nome"] = tipos[0].get_tipo_display() if tipos else "Exame"
        context["recepcao"] = "Recepção 2"
        context["cpf"] = encaixe.cpf
    else:
        context["paciente_nome"] = "Paciente"
        context["exame_nome"] = "Exame"
        context["recepcao"] = "Recepção"
        context["cpf"] = ""

    return render(request, "system/checagem_documentos.html", context)









@xframe_options_sameorigin

def visualizar_agendamento_view(request):

    """Renderiza a tela de visualizar agendamento"""

    context = {}

    return render(request, "system/visualizar_agendamento.html", context)





def screen_view(request, screen_slug):

    """Thin view: only render context produced by the application service."""

    context = get_screen_context(screen_slug)

    if context is None:

        raise Http404("Tela não encontrada")

    return render(request, "core/screen.html", context)





@xframe_options_sameorigin

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

def agendamento_nao_encontrado_view(request):

    return render(request, 'mobile/agendamento_nao_encontrado.html')





@xframe_options_sameorigin

def login_view(request):

    """Tela de Login — autentica paciente ou staff pelo CPF + senha."""

    if request.session.get("staff_logged_in"):

        if request.GET.get("interno") != "1":

            return redirect("sistema-interno")

    if request.method == "POST":

        form = LoginPacienteForm(request.POST)

        if form.is_valid():

            usuario = form.cleaned_data.get("usuario_autenticado")

            paciente = form.cleaned_data.get("paciente_autenticado")



            request.session["staff_logged_in"] = True

            if usuario:

                request.session["staff_usuario_id"] = usuario.pk

            if paciente:

                request.session["paciente_id"] = paciente.pk

            return redirect("sistema-interno")

        context = {**get_login_context(), "form": form}

        return render(request, "mobile/login.html", context)

    context = {**get_login_context(), "form": LoginPacienteForm()}

    return render(request, "mobile/login.html", context)





@xframe_options_sameorigin

def cadastro_view(request):

    """Tela de Cadastro — persiste o paciente no banco com tratamento de erros."""

    if request.method == "POST":

        form = CadastroPacienteForm(request.POST)

        if form.is_valid():

            try:

                paciente = form.save()

                request.session["paciente_id"] = paciente.pk

                return redirect("login")

            except IntegrityError:

                form.add_error(None, "Erro ao salvar: CPF ou e-mail já cadastrado.")

        context = {**get_cadastro_context(), "form": form}

        return render(request, "mobile/cadastro.html", context)

    context = {**get_cadastro_context(), "form": CadastroPacienteForm()}

    return render(request, "mobile/cadastro.html", context)





def logout_view(request):

    request.session.flush()

    return redirect("login")





def area_paciente_view(request):

    """Placeholder pós-login: substituir pela próxima tela do fluxo do paciente."""

    paciente_id = request.session.get("paciente_id")

    if not paciente_id:

        return redirect("login")



    context = {"page_title": "Área do Paciente"}

    return render(request, "mobile/area_paciente.html", context)





@xframe_options_sameorigin

def gestao_qualidade_view(request):

    return render(request, 'system/gestao_qualidade.html', {

        "interno": request.GET.get("interno") == "1",

        "usuario_logado": _usuario_logado(request),

    })





@xframe_options_sameorigin

def pesquisa_satisfacao_view(request):

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





@require_POST

def encaixe_view(request):

    """Recebe o formulário de encaixe, persiste e retorna JSON com a senha gerada."""

    form = EncaixeForm(request.POST, request.FILES)

    if form.is_valid():

        try:

            encaixe = registrar_encaixe(form.cleaned_data, arquivo=request.FILES.get("anexo"))

            return JsonResponse({"ok": True, "senha": encaixe.senha, "posicao": encaixe.posicao_fila})

        except Exception as e:

            return JsonResponse({"ok": False, "erros": {"__all__": [str(e)]}}, status=500)



    return JsonResponse({"ok": False, "erros": form.errors}, status=400)





@require_POST

@staff_required

def validar_encaixe_view(request, encaixe_id):

    """Transiciona VALIDACAO â†’ AGUARDANDO."""

    encaixe = get_object_or_404(EncaixePaciente, pk=encaixe_id)

    if encaixe.status != EncaixePaciente.Status.VALIDACAO:

        return JsonResponse({"ok": False, "erro": "Status inválido para validação."}, status=400)

    encaixe.status = EncaixePaciente.Status.AGUARDANDO

    encaixe.save(update_fields=["status"])

    notificar_fila_atualizada()

    return JsonResponse({"ok": True})





@require_POST

@staff_required

def iniciar_atendimento_view(request, encaixe_id):

    """Transiciona CHAMADO â†’ ATENDIMENTO."""

    encaixe = get_object_or_404(EncaixePaciente, pk=encaixe_id)

    if encaixe.status != EncaixePaciente.Status.CHAMADO:

        return JsonResponse({"ok": False, "erro": "Paciente não foi chamado."}, status=400)

    encaixe.status = EncaixePaciente.Status.ATENDIMENTO

    encaixe.save(update_fields=["status"])

    notificar_fila_atualizada()
    notificar_paciente(
        encaixe.cpf,
        "paciente.atendimento",
        senha=encaixe.senha,
        nome=encaixe.nome_completo,
        sala=encaixe.sala,
        timestamp=timezone.now().isoformat(),
    )

    return JsonResponse({"ok": True})





@require_POST

@staff_required

def concluir_atendimento_view(request, encaixe_id):

    """Transiciona ATENDIMENTO â†’ CONCLUIDO."""

    encaixe = get_object_or_404(EncaixePaciente, pk=encaixe_id)

    if encaixe.status != EncaixePaciente.Status.ATENDIMENTO:

        return JsonResponse({"ok": False, "erro": "Atendimento nÃ£o estÃ¡ em andamento."}, status=400)
    encaixe.status = EncaixePaciente.Status.CONCLUIDO
    encaixe.concluido_em = timezone.now()

    encaixe.save(update_fields=["status", "concluido_em"])

    notificar_fila_atualizada()
    notificar_paciente(
        encaixe.cpf,
        "paciente.concluido",
        senha=encaixe.senha,
        nome=encaixe.nome_completo,
        timestamp=timezone.now().isoformat(),
    )

    from django.conf import settings
    from core.integrador import IntegradorHttp

    base_url = getattr(settings, "INTEGRADOR_BASE_URL", "")
    if base_url:
        token = getattr(settings, "INTEGRADOR_TOKEN", "")
        integrador = IntegradorHttp(base_url=base_url, token=token)
        integrador.notificar_conclusao(encaixe)

    return JsonResponse({

        "ok": True,

        "redirect_url": f"/pesquisa-satisfacao/?cpf={encaixe.cpf}",

    })



@xframe_options_sameorigin

def meu_perfil_view(request):

    def _iniciais(nome):

        partes = (nome or "").split()

        return "".join(p[0] for p in partes[:2]).upper() or "?"



    def _ctx(interno, usuario, paciente, form, extra=None):

        instancia = paciente or usuario

        nome = instancia.nome_completo if instancia else "Sem vínculo"

        ctx = {

            "interno": interno,

            "usuario": usuario,

            "paciente": paciente,

            "form": form,

            "cpf_perfil": instancia.cpf if instancia else "",

            "nome_perfil": nome,

            "iniciais_perfil": _iniciais(nome),

            "papel_perfil": usuario.get_nivel_acesso_display() if usuario else "Paciente",

        }

        if extra:

            ctx.update(extra)

        return ctx



    interno = request.GET.get("interno") == "1"



    if not request.session.get("staff_logged_in"):

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


def dashboard_metrics_export(request):
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

    from datetime import date
    from core.integrador import sincronizar_agendamentos

    data_str = request.POST.get("data", "")
    data_alvo = date.fromisoformat(data_str) if data_str else None
    resultado = sincronizar_agendamentos(data_alvo=data_alvo)
    return JsonResponse(resultado)



