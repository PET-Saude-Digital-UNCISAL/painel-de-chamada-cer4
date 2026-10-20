"""Servicos da area interna ("sistema"): listagem/definicao de telas
(ScreenDefinition, SCREEN_DEFINITIONS, list_patient_screens,
list_team_screens, get_screen_context), o contexto do dashboard de
monitoramento, e a auditoria de percurso (filtros, contexto, helpers de
data). Quarta e ultima fatia da divisao por dominio da Fase 3.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from django.urls import reverse
from django.utils import timezone

from core.clock import SystemClock
from core.models import EncaixePaciente


@dataclass(frozen=True)

class ScreenDefinition:

    """Um item da lista de telas isoladas de desenvolvimento (ver
    SCREEN_DEFINITIONS abaixo) -- usado pra montar os cards do painel de
    telas e resolver a rota generica /telas/<slug>/ em screen_view."""

    slug: str

    title: str

    owner: str

    status: str


# Catalogo das telas isoladas visitaveis pela rota generica
# /telas/<slug>/ (screen_view) e listadas no painel de desenvolvimento --
# cada entrada vira um card com titulo, responsavel e status.
SCREEN_DEFINITIONS = [

    # Telas individuais que aparecerão em seus próprios cards

    ScreenDefinition("pacientes-listagem", "Listagem de Pacientes", "Dev 1", "em desenvolvimento"),

    ScreenDefinition("dev2", "Tela de Triagem", "Dev 2", "em desenvolvimento"),

    ScreenDefinition("dev3", "Tela de Chamadas", "Dev 3", "em desenvolvimento"),

    ScreenDefinition("dev4", "Tela de Presença", "Dev 4", "em desenvolvimento"),
    ScreenDefinition("perdeu-chamada", "Senha Perdida (Perdeu Chamada)", "Daniely Vasconcelos", "concluída"),

    ScreenDefinition(

        "auditoria-percurso-seguranca",

        "Auditoria de Percurso e Segurança",

        "Daniely Vasconcelos",

        "em desenvolvimento",

    ),

]


def get_dashboard_monitoramento_context() -> dict:

    """Return the temporary mock payload displayed by the monitoring dashboard."""

    return {

        "page_title": "Monitoramento do Fluxo",

        "current_time": "09:48",

        "current_date": "05 de maio de 2026",

        "system_status": "Sistema online",

        "user": {

            "initial": "F",

            "name": "Funcionário",

            "role": "Gestão da recepção",

        },

        "kpis": [

            {

                "title": "Check-ins recebidos",

                "value": "142",

                "footer": "TOTAL VALIDADO",

                "is_primary": True,

                "badge_class": "green",

                "badge_text": "12%",

                "badge_direction": "up",

            },

            {

                "title": "Recepção 1",

                "value": "12",

                "footer": "pacientes em fluxo",

                "badge_class": "green",

                "badge_text": "ESTÁVEL",

                "badge_direction": "up",

            },

            {

                "title": "Recepção 2",

                "value": "8",

                "footer": "atendimentos ativos",

                "badge_class": "green",

                "badge_text": "ESTÁVEL",

                "badge_direction": "up",

            },

            {

                "title": "Pendências e retenções",

                "value": "8",

                "footer": "3 retidos • Média +25m",

                "badge_class": "red",

                "badge_text": "ALERTA",

                "badge_direction": "down",

            },

            {

                "title": "Recepção 3",

                "value": "5",

                "footer": "pacientes aguardando",

                "badge_class": "green",

                "badge_text": "ESTÁVEL",

                "badge_direction": "up",

            },

            {

                "title": "Salas ativas",

                "value": "24",

                "footer": "24 em operação",

                "badge_class": "green",

                "badge_text": "NORMAL",

                "badge_dot": True,

            },

        ],

        "chart": {

            "title": "Visão Geral do Fluxo",

            "subtitle": "Entrada de pacientes por dia",

            "bars": [

                {"label": "SEG", "height": 60},

                {"label": "TER", "height": 40},

                {"label": "QUA", "height": 70},

                {"label": "QUI", "height": 45},

                {"label": "SEX", "height": 85},

                {"label": "SAB", "height": 30},

                {"label": "DOM", "height": 25},

            ],

        },

        "encaixes": {

            "title": "Controle de encaixes",

            "pending_count": "7 solicitações pendentes",

            "pending_chip": "+4 solicitações",

            "expanded_chip": "7 exibidas",

            "link_label": "Ver todos",

            "collapse_label": "Mostrar menos",

            "requests": [

                {"name": "Roberto Almeida", "mother": "Helena Almeida", "specialty": "Fonoaudiologia", "time": "08:15"},

                {"name": "Marta Ribeiro", "mother": "Sônia Ribeiro", "specialty": "Fonoaudiologia", "time": "08:30"},

                {"name": "José Fernando", "mother": "Maria de Lourdes Silva", "specialty": "Fisioterapia", "time": "08:30"},

                {"name": "Ana Paula Santos", "mother": "Francisca Santos", "specialty": "Terapia Ocupacional", "time": "08:45"},

                {"name": "Carlos Henrique Lima", "mother": "Rosângela Lima", "specialty": "Psicologia", "time": "09:00"},

                {"name": "Beatriz Souza Costa", "mother": "Adriana Souza", "specialty": "Fisioterapia", "time": "09:15"},

                {"name": "Lucas Gabriel Rocha", "mother": "Patrícia Rocha", "specialty": "Fonoaudiologia", "time": "09:30"},

            ],

        },

        "kanban_columns": [

            {

                "title": "Validação",

                "count": 8,

                "footer_text": "+5 pacientes na fila",

                "footer_link": "Ver todos",

                "patients": [

                    {

                        "initial": "J",

                        "name": "João Pedro Alves",

                        "mother": "Renata Alves",

                        "avatar_class": "light",

                        "action_label": "Validar Check-in",

                        "history": "Check-in: 08:05 • Aguardando validação",

                        "status_dot": "blue",

                        "status_label": "Geral",

                        "status_time": "12m",

                    },

                    {

                        "initial": "M",

                        "name": "Maria Silva Costa",

                        "mother": "Ana Costa",

                        "avatar_class": "red",

                        "overdue": True,

                        "warning": "Falta RG Original",

                        "action_label": "Validar Check-in",

                        "history": "Pendência registrada às 08:12",

                        "status_dot": "orange",

                        "status_label": "Atenção",

                        "status_time": "59m • Atraso",

                        "status_time_class": "red",

                    },

                    {

                        "initial": "C",

                        "name": "Carmem Lucia Souza",

                        "mother": "Tereza Souza",

                        "avatar_class": "red",

                        "overdue": True,

                        "warning": "Choque: Fisio + Fono",

                        "action_label": "Validar Check-in",

                        "history": "Pendência registrada às 08:12",

                        "status_dot": "red",

                        "status_label": "Prior. 80+",

                        "status_time": "45m • Atraso",

                        "status_time_class": "red",

                    },

                ],

            },

            {

                "title": "Aguardando",

                "count": 5,

                "footer_text": "+2 pacientes na fila",

                "footer_link": "Ver todos",

                "patients": [

                    {

                        "initial": "T",

                        "name": "Tatiana Moreira",

                        "mother": "Lúcia Moreira",

                        "avatar_class": "light",

                        "history": "Check-in: 07:52 • Aguardando atendimento",

                        "status_dot": "orange",

                        "status_label": "Atenção",

                        "status_time": "18m",

                    },

                    {

                        "initial": "J",

                        "name": "José Carlos Santos",

                        "mother": "Maria Santos",

                        "avatar_class": "light",

                        "history": "Check-in: 08:05 • Aguardando atendimento",

                        "status_dot": "blue",

                        "status_label": "Geral",

                        "status_time": "5m",

                    },

                    {

                        "initial": "A",

                        "name": "Ana Beatriz Souza",

                        "mother": "Claudia Souza",

                        "avatar_class": "light",

                        "history": "Check-in: 08:05 • Aguardando atendimento",

                        "status_dot": "blue",

                        "status_label": "Geral",

                        "status_time": "2m",

                    },

                ],

            },

            {

                "title": "Em atendimento",

                "count": 5,

                "footer_text": "+2 em atendimento",

                "footer_link": "Ver todos",

                "patients": [

                    {

                        "initial": "M",

                        "name": "Mariana Lima",

                        "mother": "Beatriz Lima",

                        "avatar_class": "light",

                        "professional": "Dra. Fernanda",

                        "room": "Sala 02",

                        "history": "Chamado: 08:30 • Entrou: 08:34",

                        "status_dot": "red",

                        "status_label": "Prior. 80+",

                        "status_time": "15m",

                    },

                    {

                        "initial": "L",

                        "name": "Lucas Ferreira",

                        "mother": "Juliana Ferreira",

                        "avatar_class": "light",

                        "professional": "Dr. Alexandre",

                        "room": "Sala 04",

                        "history": "Chamado: 08:30 • Entrou: 08:34",

                        "status_dot": "blue",

                        "status_label": "Geral",

                        "status_time": "30m",

                    },

                    {

                        "initial": "C",

                        "name": "Cláudia Martins",

                        "mother": "Vera Martins",

                        "avatar_class": "light",

                        "professional": "Dr. Renato",

                        "room": "Sala 01",

                        "history": "Chamado: 08:25 • Entrou: 08:28",

                        "status_dot": "blue",

                        "status_label": "Geral",

                        "status_time": "22m",

                    },

                ],

            },

            {

                "title": "Finalizados",

                "count": 4,

                "footer_text": "+1 finalizado",

                "footer_link": "Ver todos",

                "patients": [

                    {

                        "initial": "R",

                        "name": "Roberto Dias",

                        "mother": "Camila Dias",

                        "avatar_class": "light",

                        "completed": True,

                        "completion_time": "Concluído às 08:55",

                    },

                    {

                        "initial": "P",

                        "name": "Patrícia Almeida",

                        "mother": "Glória Almeida",

                        "avatar_class": "light",

                        "completed": True,

                        "completion_time": "Concluído às 08:42",

                    },

                    {

                        "initial": "E",

                        "name": "Eduardo Coelho",

                        "mother": "Silvia Coelho",

                        "avatar_class": "light",

                        "completed": True,

                        "completion_time": "Concluído às 08:31",

                    },

                ],

            },

        ],

    }


def list_patient_screens() -> list[dict]:

    """Return the canonical navigation cards for patient-facing screens."""

    return [

        {

            "slug": "identificacao-paciente",

            "title": "Identificação do Paciente",

            "owner": "Remany",

            "path": reverse("identificacao-paciente"),

        },

        {

            "slug": "checkin-concluido",

            "title": "Check-in Concluído",

            "owner": "Remany",

            "path": reverse("checkin-concluido"),

        },

        {

            "slug": "acompanhamento-atendimento",

            "title": "Acompanhamento de Atendimento",

            "owner": "Remany",

            "path": reverse("acompanhamento-atendimento"),

        },

        {

            "slug": "paciente-chamado",

            "title": "Paciente Chamado",

            "owner": "Remany",

            "path": reverse("paciente-chamado"),

        },

        {

            "slug": "checkin-assistido",

            "title": "Check-in Assistido",

            "owner": "Remany",

            "path": reverse("checkin-assistido"),

        },

        {

            "slug": "bloqueio-direcionamento",

            "title": "Bloqueio e Direcionamento",

            "owner": "Remany",

            "path": reverse("bloqueio-direcionamento"),

        },

        {

            "slug": "pesquisa-satisfacao",

            "title": "Pesquisa de satisfação",

            "owner": "Monaliza",

            "path": reverse("pesquisa_satisfacao"),

        },

        {

            "slug": "agendamento-nao-encontrado",

            "title": "Agendamento não encontrado",

            "owner": "Monaliza",

            "path": reverse("agendamento_nao_encontrado"),

        },

        {

            "slug": "perdeu-chamada",

            "title": "Perdeu a chamada",

            "owner": "Monaliza",

            "path": reverse("perdeu_chamada"),

        },

        {

            "slug": "visualizar-agendamento",

            "title": "Visualizar Agendamento",

            "owner": "Cristian",

            "path": reverse("screen-visualizar-agendamento"),

        },

        {

            "slug": "checagem-documentos",

            "title": "Checagem de Documentos",

            "owner": "Cristian",

            "path": reverse("screen-checagem-documentos"),

        },

    ]


def list_team_screens() -> list[dict]:

    """Return cards used by the dashboard and direct route links."""

    # Agrupando telas relacionadas a Pacientes

    pacientes_group = {

        "is_group": True,

        "title": "Telas de Pacientes",

        "screens": [

            {

                "slug": "agendamento-nao-encontrado",

                "title": "Tela de Agendamento Não Encontrado",

                "owner": "Monaliza",

                "status": "Concluído",

                "path": "/agendamento-nao-encontrado/",

            },

            {

                "slug": "perdeu-chamada",

                "title": "Tela de Senha Perdida",

                "owner": "Monaliza",

                "status": "Concluído",

                "path": "/perdeu-chamada/",

            },

        ],

    }

 

    # Outras telas que não estão no grupo

    other_screens = [

        {"slug": s.slug, "title": s.title, "owner": s.owner, "status": s.status, "path": f"/telas/{s.slug}/"}

        for s in SCREEN_DEFINITIONS

        if s.slug not in ["pacientes-listagem", "perdeu-chamada"]

    ]

    other_screens.append(

        {

            "slug": "dashboard-monitoramento",

            "title": "Dashboard de Monitoramento do Fluxo",

            "owner": "Remany",

            "status": "em desenvolvimento",

            "path": "/dashboard-monitoramento/",

        }

    )



    other_screens.append(

        {

            "slug": "painel-chamada",

            "title": "Painel de Chamada da Recepção",

            "owner": "Remany",

            "status": "em desenvolvimento",

            "path": "/painel-chamada/",

        }

    )



    other_screens.append(

        {

            "slug": "paciente-chamado",

            "title": "Paciente Chamado",

            "owner": "Remany",

            "status": "em desenvolvimento",

            "path": "/paciente-chamado/",

        }

    )



    other_screens.append(

        {

            "slug": "acompanhamento-atendimento",

            "title": "Acompanhamento de Atendimento",

            "owner": "Remany",

            "status": "em desenvolvimento",

            "path": "/acompanhamento-atendimento/",

        }

    )



    other_screens.append(

        {

            "slug": "checkin-concluido",

            "title": "Check-in Concluído",

            "owner": "Remany",

            "status": "em desenvolvimento",

            "path": "/checkin-concluido/",

        }

    )



    other_screens.append(

        {

            "slug": "checkin-assistido",

            "title": "Check-in Assistido",

            "owner": "Remany",

            "status": "em desenvolvimento",

            "path": "/checkin-assistido/",

        }

    )



    other_screens.append(

        {

            "slug": "configuracoes",

            "title": "Tela de Configurações",

            "owner": "Daniely Vasconcelos",

            "status": "Concluído",

            "path": "/configuracoes/",

        }

    )



    other_screens.append(

        {

            "slug": "login",

            "title": "Tela de Login (Acesso ao Portal)",

            "owner": "Nathalia",

            "status": "Concluído",

            "path": "/login/",

        }

    )



    other_screens.append(

        {

            "slug": "cadastro",

            "title": "Tela de Cadastro (Criar Conta do Paciente)",

            "owner": "Nathalia",

            "status": "Concluído",

            "path": "/cadastro/",

        }

    )



    return [pacientes_group] + other_screens


def get_screen_context(screen_slug: str) -> Optional[dict]:

    """Build template context for one screen.



    Returns None when the slug is unknown.

    """

    found = next((item for item in SCREEN_DEFINITIONS if item.slug == screen_slug), None)

    if found is None:

        return None

 

    return {

        "title": found.title,

        "screen_slug": found.slug,

        "owner": found.owner,

        "status": found.status,

        "header": f"{found.title} ({found.slug})",

        "items": [

            {"label": "Atendimentos ativos", "value": 12},

            {"label": "Fila de espera", "value": 5},

            {"label": "Última atualização", "value": "agora"},

        ],

    }


def _only_digits(value: str) -> str:

    """Remove tudo que nao for digito -- usado pra normalizar CPF nos
    filtros de busca da auditoria de percurso."""

    return "".join(ch for ch in value if ch.isdigit())


def _parse_iso_date(value: str) -> Optional[date]:

    """Converte uma data ISO (AAAA-MM-DD) vinda de querystring/filtro em
    date; devolve None se o valor estiver vazio ou for invalido, em vez
    de propagar excecao pro chamador tratar."""

    try:

        return date.fromisoformat((value or "").strip())

    except ValueError:

        return None


def _resolve_auditoria_date_range(filtros_dict: dict) -> tuple[Optional[date], Optional[date]]:

    """Return an inclusive date range for audit filtering.

    Defaults to today when no filter is provided."""

    single_date = _parse_iso_date(filtros_dict.get("data") or "")

    if single_date:

        return single_date, single_date



    start_date = _parse_iso_date(filtros_dict.get("data_inicio") or "")

    end_date = _parse_iso_date(filtros_dict.get("data_fim") or "")



    if start_date and end_date and start_date > end_date:

        return end_date, start_date



    if start_date or end_date:

        return start_date, end_date



    hoje = timezone.localdate()

    return hoje, hoje


def _build_date_filter_modal_context(filtros_dict: dict, today: date) -> dict:

    """Monta a grade de dias do mini-calendario do filtro de data da
    auditoria de percurso: um dict por dia do mes de referencia (o mes do
    inicio do intervalo filtrado, ou o mes atual se nao ha filtro), com
    espacos vazios preenchidos no inicio/fim pra fechar a grade em
    semanas completas, e marcando quais dias caem dentro do intervalo
    selecionado."""

    start_date, end_date = _resolve_auditoria_date_range(filtros_dict)

    month_reference = start_date or today

    month_start = date(month_reference.year, month_reference.month, 1)

    month_end = date(month_reference.year, month_reference.month, monthrange(month_reference.year, month_reference.month)[1])



    calendar_days = [{"value": "", "iso": "", "is_selected": False, "is_muted": True} for _ in range(month_start.weekday())]

    cursor = month_start

    while cursor <= month_end:

        calendar_days.append(

            {

                "value": cursor.day,

                "iso": cursor.isoformat(),

                "is_selected": bool(start_date and end_date and start_date <= cursor <= end_date),

                "is_muted": False,

            }

        )

        cursor += timedelta(days=1)



    while len(calendar_days) % 7:

        calendar_days.append({"value": "", "iso": "", "is_selected": False, "is_muted": True})



    month_names = {

        1: "Janeiro",

        2: "Fevereiro",

        3: "Março",

        4: "Abril",

        5: "Maio",

        6: "Junho",

        7: "Julho",

        8: "Agosto",

        9: "Setembro",

        10: "Outubro",

        11: "Novembro",

        12: "Dezembro",

    }



    current_month_start = date(today.year, today.month, 1)

    current_month_end = date(today.year, today.month, monthrange(today.year, today.month)[1])



    return {

        "data_inicio": (start_date or month_start).isoformat(),

        "data_fim": (end_date or month_end).isoformat(),

        "month_label": f"{month_names[month_reference.month]} {month_reference.year}",

        "weekdays": ["D", "S", "T", "Q", "Q", "S", "S"],

        "calendar_days": calendar_days,

        "today": today.isoformat(),

        "last_7_start": (today - timedelta(days=6)).isoformat(),

        "month_start": current_month_start.isoformat(),

        "month_end": current_month_end.isoformat(),

    }


STATUS_DISPLAY = {

    EncaixePaciente.Status.VALIDACAO: "EM VALIDAÇÃO",

    EncaixePaciente.Status.AGUARDANDO: "AGUARDANDO",

    EncaixePaciente.Status.CHAMADO: "CHAMADO",

    EncaixePaciente.Status.ATENDIMENTO: "EM ATENDIMENTO",

    EncaixePaciente.Status.CONCLUIDO: "FINALIZADO",

    EncaixePaciente.Status.AUSENTE: "AUSENTE",

}


STATUS_CLASS = {

    EncaixePaciente.Status.VALIDACAO: "wait",

    EncaixePaciente.Status.AGUARDANDO: "wait",

    EncaixePaciente.Status.CHAMADO: "ok",

    EncaixePaciente.Status.ATENDIMENTO: "ok",

    EncaixePaciente.Status.CONCLUIDO: "ok",

    EncaixePaciente.Status.AUSENTE: "alert",

}


def filtrar_auditoria(filtros_dict: dict) -> list[dict]:

    """Consulta encaixes reais do banco e aplica os filtros."""

    from django.db.models import Q

    from django.utils import timezone as tz



    termo = (filtros_dict.get("q") or "").strip().lower()

    termo_digitos = _only_digits(termo)

    data_inicio, data_fim = _resolve_auditoria_date_range(filtros_dict)

    status_filtro = (filtros_dict.get("status") or "").strip().upper()

    setor_filtro = (filtros_dict.get("setor") or "").strip()



    qs = EncaixePaciente.objects.prefetch_related("tipos_atendimento").all().order_by("data_atendimento", "posicao_fila")



    if termo:

        q_nome = Q(nome_completo__icontains=termo)

        q_ficha = Q(senha__icontains=termo)

        q_cpf = Q()

        if termo_digitos:

            q_cpf = Q(cpf__contains=termo_digitos)

        qs = qs.filter(q_nome | q_ficha | q_cpf)



    if data_inicio:

        qs = qs.filter(data_atendimento__gte=data_inicio)

    if data_fim:

        qs = qs.filter(data_atendimento__lte=data_fim)



    if status_filtro and status_filtro != "TODOS":

        status_map = {v.upper(): k for k, v in STATUS_DISPLAY.items()}

        mapped = status_map.get(status_filtro)

        if mapped:

            qs = qs.filter(status=mapped)



    if setor_filtro and setor_filtro != "Todos":

        pass  # EncaixePaciente nao tem campo setor



    pacientes = []

    for idx, e in enumerate(qs, start=1):

        tipos = list(e.tipos_atendimento.all())

        chamada = tz.localtime(e.chamado_em).strftime("%H:%M:%S") if e.chamado_em else "--------"



        encerramento = "--------"

        if e.status == EncaixePaciente.Status.CONCLUIDO:

            encerramento = tz.localtime(e.concluido_em or e.chamado_em or e.criado_em).strftime("%H:%M:%S")



        pacientes.append({

            "id": e.pk,

            "ordem": idx,

            "ficha": e.senha,

            "nome": e.nome_completo,

            "status_raw": e.status,

            "sala": e.sala or "",

            "cpf": e.cpf,

            "badges": [t.get_tipo_display() for t in tipos],

            "check_in": tz.localtime(e.criado_em).strftime("%H:%M:%S"),

            "entrada_fila": tz.localtime(e.criado_em).strftime("%H:%M:%S"),

            "chamada": chamada,

            "encerramento": encerramento,

            "status": STATUS_DISPLAY.get(e.status, e.status),

            "status_class": STATUS_CLASS.get(e.status, "wait"),

            "log": e.justificativa or "—",

            "data_referencia": e.data_atendimento.isoformat(),

            "setor": "Recepção",

        })



    return pacientes


def get_auditoria_percurso_context(filtros_dict: Optional[dict] = None) -> dict:

    """Context used by the dedicated audit screen template."""

    filtros_dict = filtros_dict or {}

    now = SystemClock.now()

    month_names = {

        1: "janeiro",

        2: "fevereiro",

        3: "marco",

        4: "abril",

        5: "maio",

        6: "junho",

        7: "julho",

        8: "agosto",

        9: "setembro",

        10: "outubro",

        11: "novembro",

        12: "dezembro",

    }

    current_date = f"{now.day:02d} de {month_names[now.month]} de {now.year}"

    pacientes = filtrar_auditoria(filtros_dict)

    alertas = sum(1 for paciente in pacientes if paciente["status_class"] == "alert")

    data_inicio, data_fim = _resolve_auditoria_date_range(filtros_dict)



    filtros = {

        "q": (filtros_dict.get("q") or "").strip(),

        "data": (filtros_dict.get("data") or "").strip(),

        "data_inicio": data_inicio.isoformat() if data_inicio else "",

        "data_fim": data_fim.isoformat() if data_fim else "",

        "setor": (filtros_dict.get("setor") or "Recepção").strip() or "Recepção",

        "status": ((filtros_dict.get("status") or "TODOS").strip() or "TODOS").upper(),

        "apenas_alertas": str(filtros_dict.get("apenas_alertas") or "").lower() in {"1", "true", "on", "yes"},

    }



    return {

        "page_title": "CER III — Atendimentos do Dia",

        "current_time": now.strftime("%H:%M"),

        "current_date": current_date,

        "system_status": "Sistema online",

        "user_initial": "F",

        "user_name": "Funcionário",

        "user_role": "Gestão da recepção",

        "search_placeholder": "Buscar por Paciente ou CPF...",

        "sector_selected": filtros["setor"],

        "setores_disponiveis": ["Recepção"],

        "status_disponiveis": ["TODOS"] + list(STATUS_DISPLAY.values()),

        "date_filter_modal": _build_date_filter_modal_context(filtros_dict, now.date()),

        "filtros": filtros,

        "pacientes": pacientes,

        "total_registros": len(pacientes),

        "tempo_medio_espera": "--:--",

        "alertas_auditoria": 0,

        "pagina": 1,

        "total_paginas": 1,

    }
