"""Application services for isolated screen rendering.
 
Humble Object approach:
- Views call these functions and only render context.
- Business/data assembly lives here.
"""

from base64 import b64encode
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from mimetypes import guess_type
from pathlib import Path
from typing import Optional

from core.clock import SystemClock
from core.models import EncaixePaciente, Paciente, TipoAtendimentoEncaixe


@dataclass(frozen=True)
class ScreenDefinition:
    slug: str
    title: str
    owner: str
    status: str
 
 
SCREEN_DEFINITIONS = [
    # Telas individuais que aparecerão em seus próprios cards
    ScreenDefinition("pacientes-listagem", "Listagem de Pacientes", "Dev 1", "em desenvolvimento"),
    ScreenDefinition("dev2", "Tela de Triagem", "Dev 2", "em desenvolvimento"),
    ScreenDefinition("dev3", "Tela de Chamadas", "Dev 3", "em desenvolvimento"),
    ScreenDefinition("dev4", "Tela de Presença", "Dev 4", "em desenvolvimento"),
    ScreenDefinition("dev5", "Tela de Relatórios", "Dev 5", "em desenvolvimento"),
    ScreenDefinition("perdeu-chamada", "Senha Perdida (Perdeu Chamada)", "Daniely Vasconcelos", "concluída"),
    ScreenDefinition(
        "auditoria-percurso-seguranca",
        "Auditoria de Percurso e Segurança",
        "Daniely Vasconcelos",
        "em desenvolvimento",
    ),
]


AUDITORIA_MOCK_DATA = [
    {
        "ficha": "A011",
        "nome": "Benedito Silveira Santos",
        "cpf": "001.234.567-89",
        "badges": ["80+", "Prioritario"],
        "check_in": "08:12:45",
        "entrada_fila": "08:14:02",
        "chamada": "08:15:30",
        "encerramento": "08:45:12",
        "status": "ATENDIDO",
        "status_class": "ok",
        "log": "—",
        "data_referencia": "2026-07-07",
        "setor": "Recepção",
    },
    {
        "ficha": "A012",
        "nome": "Ricardo Mendes Junior",
        "cpf": "452.112.338-00",
        "badges": [],
        "check_in": "08:30:11",
        "entrada_fila": "08:32:55",
        "chamada": "09:15:00*",
        "encerramento": "09:42:18",
        "status": "ATENDIDO",
        "status_class": "ok",
        "log": "—",
        "data_referencia": "2026-07-07",
        "setor": "Recepção",
    },
    {
        "ficha": "A013",
        "nome": "Maria Clara Ferreira",
        "cpf": "882.331.002-12",
        "badges": [],
        "check_in": "09:45:38",
        "entrada_fila": "09:48:12",
        "chamada": "--------",
        "encerramento": "--------",
        "status": "AGUARDANDO",
        "status_class": "wait",
        "log": "ALT: ANA SILVA | Motivo: Paciente atrasado | Horário: 09:15",
        "data_referencia": "2026-07-06",
        "setor": "Triagem",
    },
    {
        "ficha": "A014",
        "nome": "Antônio Oliveira",
        "cpf": "123.444.555-66",
        "badges": ["Atrasado"],
        "check_in": "09:50:22",
        "entrada_fila": "--------",
        "chamada": "--------",
        "encerramento": "--------",
        "status": "PENDÊNCIA",
        "status_class": "alert",
        "log": "—",
        "data_referencia": "2026-07-07",
        "setor": "Enfermagem",
    },
]


PAINEL_CHAMADA_ASSETS_DIR = Path(__file__).resolve().parent / "static" / "core" / "painel_chamada" / "assets"


@lru_cache
def _get_painel_chamada_asset_data_url(relative_path: str) -> str:
    asset_path = PAINEL_CHAMADA_ASSETS_DIR / relative_path
    content_type = guess_type(asset_path.name)[0] or "application/octet-stream"
    encoded_content = b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:{content_type};base64,{encoded_content}"


def get_painel_chamada_context() -> dict:
    return {
        "page_title": "Painel de Chamada",
        "reception_name": "RECEPÇÃO 3",
        "weekday": "SEGUNDA-FEIRA,",
        "current_date": "27 DE ABRIL DE 2026",
        "current_time": "10:48",
        "current_call": {
            "ticket": "A011",
            "patient_name": "FELIPE DA SILVA",
            "room": "SALA 04",
            "service_type": "AMBULATORIAL",
        },
        "recent_calls": [
            {
                "ticket": "A010",
                "room": "SALA 02",
                "patient_name": "MARIA DA SILVA",
                "time": "10:48",
            },
            {
                "ticket": "B005",
                "room": "SALA 03",
                "patient_name": "MARIA JOSÉ",
                "time": "10:48",
                "highlighted": True,
            },
            {
                "ticket": "A009",
                "room": "SALA 06",
                "patient_name": "ABRAÃO FARIAS DE LIMA",
                "time": "10:48",
            },
            {
                "ticket": "A008",
                "room": "SALA 05",
                "patient_name": "JOÃO PEDRO MIGUEL",
                "time": "10:48",
            },
            {
                "ticket": "A007",
                "room": "SALA 01",
                "patient_name": "LUCAS FERREIRA",
                "time": "10:48",
            },
        ],
        "notice_items": [
            "DIRIJA-SE À SUA SALA AO SER CHAMADO",
            "FIQUE ATENTO AO SINAL SONORO DA CHAMADA",
            "RESPEITE A ORDEM DAS FILAS",
            "HOJE É SEGUNDA-FEIRA, 27 DE ABRIL DE 2026",
        ],
        "qr_code_url": _get_painel_chamada_asset_data_url("qr-code-temporario.png"),
        "libras_avatar_url": _get_painel_chamada_asset_data_url("libras-avatar-temporario.png"),
        "logo_cer_url": _get_painel_chamada_asset_data_url("logo-cer.svg"),
        "logo_uncisal_url": _get_painel_chamada_asset_data_url("logo-uncisal.svg"),
        "logo_sus_url": _get_painel_chamada_asset_data_url("logo-sus.png"),
        "clock_card_url": _get_painel_chamada_asset_data_url("clock-card.svg"),
        "libras_icon_url": _get_painel_chamada_asset_data_url("libras-icon.svg"),
        "call_bell_icon_url": _get_painel_chamada_asset_data_url("call-bell-icon.png"),
        "room_icon_url": _get_painel_chamada_asset_data_url("room-icon.png"),
        "service_icon_url": _get_painel_chamada_asset_data_url("service-icon.png"),
        "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),
        "chamada_audio_url": _get_painel_chamada_asset_data_url("audiobeep2.mp3"),
    }


PACIENTE_CHAMADO_ASSETS_DIR = Path(__file__).resolve().parent / "static" / "core" / "paciente_chamado" / "assets"


@lru_cache
def _get_paciente_chamado_asset_data_url(relative_path: str) -> str:
    asset_path = PACIENTE_CHAMADO_ASSETS_DIR / relative_path
    content_type = guess_type(asset_path.name)[0] or "application/octet-stream"
    encoded_content = b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:{content_type};base64,{encoded_content}"


def get_paciente_chamado_context() -> dict:
    return {
        "page_title": "Paciente Chamado",
        "title": "PACIENTE CHAMADO",
        "subtitle": "Dirija-se ao local indicado para atendimento",
        "senha": "A003",
        "paciente": "Ricardo Augusto Oliveira",
        "sala": "10",
        "tipo_atendimento": "Ambulatorial",
        "status": "Chamada atual",
        "mensagem": "Dirija-se à sala indicada acima para iniciar seu atendimento.",
        "footer_indicators": [
            {"label": "LGPD", "detail": "Conforme", "icon": "lock"},
            {"label": "Conexão", "detail": "Segura", "icon": "shield"},
        ],
        "public_sans_font_url": _get_paciente_chamado_asset_data_url("public-sans.ttf"),
    }


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
            "link_label": "Ver todos",
            "requests": [
                {"name": "Roberto Almeida", "specialty": "Fonoaudiologia", "time": "08:15"},
                {"name": "Marta Ribeiro", "specialty": "Fonoaudiologia", "time": "08:30"},
                {"name": "José Fernando", "specialty": "Fisioterapia", "time": "08:30"},
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
    return "".join(ch for ch in value if ch.isdigit())


def _parse_iso_date(value: str) -> Optional[date]:
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError:
        return None


def _resolve_auditoria_date_range(filtros_dict: dict) -> tuple[Optional[date], Optional[date]]:
    """Return an inclusive date range for audit filtering."""
    single_date = _parse_iso_date(filtros_dict.get("data") or "")
    if single_date:
        return single_date, single_date

    start_date = _parse_iso_date(filtros_dict.get("data_inicio") or "")
    end_date = _parse_iso_date(filtros_dict.get("data_fim") or "")

    if start_date and end_date and start_date > end_date:
        return end_date, start_date

    return start_date, end_date


def _build_date_filter_modal_context(filtros_dict: dict, today: date) -> dict:
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


def filtrar_auditoria(filtros_dict: dict) -> list[dict]:
    """Combina mock data com encaixes reais do banco e aplica os filtros."""
    from core.models import EncaixePaciente
    from django.utils import timezone as tz

    termo = (filtros_dict.get("q") or "").strip().lower()
    termo_digitos = _only_digits(termo)
    data_inicio, data_fim = _resolve_auditoria_date_range(filtros_dict)
    setor_filtro = (filtros_dict.get("setor") or "").strip()
    status_filtro = (filtros_dict.get("status") or "").strip().upper()
    apenas_alertas = str(filtros_dict.get("apenas_alertas") or "").lower() in {"1", "true", "on", "yes"}

    # Converte encaixes reais do banco para o mesmo formato do mock
    encaixes_qs = EncaixePaciente.objects.prefetch_related("tipos_atendimento").all()
    encaixes_como_mock = [
        {
            "ficha": e.senha,
            "nome": e.nome_completo,
            "cpf": e.cpf,
            "badges": ["Encaixe"] + [t.get_tipo_display() for t in e.tipos_atendimento.all()],
            "check_in": tz.localtime(e.criado_em).strftime("%H:%M:%S"),
            "entrada_fila": tz.localtime(e.criado_em).strftime("%H:%M:%S"),
            "chamada": "--------",
            "encerramento": "--------",
            "status": "AGUARDANDO",
            "status_class": "wait",
            "log": e.justificativa or "—",
            "data_referencia": e.data_atendimento.isoformat(),
            "setor": "Recepção",
        }
        for e in encaixes_qs
    ]

    todos = AUDITORIA_MOCK_DATA + encaixes_como_mock

    pacientes_filtrados = []
    for paciente in todos:
        if termo:
            termo_nome = termo in paciente["nome"].lower()
            termo_ficha = termo in paciente["ficha"].lower()
            termo_cpf = termo_digitos and termo_digitos in _only_digits(paciente["cpf"])
            if not (termo_nome or termo_ficha or termo_cpf):
                continue

        data_referencia = _parse_iso_date(paciente["data_referencia"])
        if data_inicio and data_referencia and data_referencia < data_inicio:
            continue
        if data_fim and data_referencia and data_referencia > data_fim:
            continue
        if setor_filtro and setor_filtro != "Todos" and paciente["setor"] != setor_filtro:
            continue
        if status_filtro and status_filtro != "TODOS" and paciente["status"] != status_filtro:
            continue
        if apenas_alertas and paciente["status_class"] != "alert":
            continue

        pacientes_filtrados.append({**paciente})

    for idx, paciente in enumerate(pacientes_filtrados, start=1):
        paciente["ordem"] = idx

    return pacientes_filtrados


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
        "setores_disponiveis": ["Recepção", "Triagem", "Enfermagem", "Todos"],
        "status_disponiveis": ["TODOS", "ATENDIDO", "AGUARDANDO", "PENDÊNCIA"],
        "date_filter_modal": _build_date_filter_modal_context(filtros_dict, now.date()),
        "filtros": filtros,
        "pacientes": pacientes,
        "total_registros": len(pacientes),
        "tempo_medio_espera": "08:42 min",
        "alertas_auditoria": alertas,
        "pagina": 1,
        "total_paginas": 8,
    }


def _cabecalho_recepcao_context(guiche: str = "RECEPÇÃO 3") -> dict:
    """Contexto compartilhado pelo cabeçalho das telas de Login e Cadastro."""
    now = SystemClock.now()
    return {
        "guiche": guiche,
        "data_atual_pt": formatar_data_pt(now.date()),
        "hora_atual": now.strftime("%H:%M"),
    }


def get_login_context() -> dict:
    """Contexto da tela de Login (Acesso ao Portal)."""
    return {
        "page_title": "Acesso ao Portal",
        **_cabecalho_recepcao_context(),
    }


def get_cadastro_context() -> dict:
    """Contexto da tela de Cadastro (Criar Conta do paciente)."""
    return {
        "page_title": "Criar Conta",
        **_cabecalho_recepcao_context(),
    }


_DIAS_PT = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
_MESES_PT = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def formatar_data_pt(d: date) -> str:
    return f"{_DIAS_PT[d.weekday()]}, {d.day:02d} de {_MESES_PT[d.month]} de {d.year}"


def autenticar_paciente(cpf: str, senha: str) -> Optional[Paciente]:
    """Retorna o Paciente se CPF e senha conferem e a conta está ativa."""
    try:
        paciente = Paciente.objects.get(cpf=cpf, paciente_ativo=True)
    except Paciente.DoesNotExist:
        return None

    if not paciente.checar_senha(senha):
        return None

    return paciente


def registrar_encaixe(cleaned_data: dict, arquivo=None) -> EncaixePaciente:
    """Gera senha, calcula posição e persiste o encaixe no banco."""
    from django.db import transaction

    hoje = SystemClock.now().date()

    with transaction.atomic():
        ultimo = (
            EncaixePaciente.objects.filter(data_atendimento=hoje)
            .order_by("-posicao_fila")
            .first()
        )
        proxima_posicao = (ultimo.posicao_fila + 1) if ultimo else 1
        senha = f"E{proxima_posicao:03d}"

        encaixe = EncaixePaciente.objects.create(
            nome_completo=cleaned_data["nome_completo"],
            cpf=cleaned_data["cpf"],
            data_nascimento=cleaned_data.get("data_nascimento"),
            nome_mae=cleaned_data.get("nome_mae", ""),
            justificativa=cleaned_data.get("justificativa", ""),
            anexo=arquivo,
            senha=senha,
            posicao_fila=proxima_posicao,
            data_atendimento=hoje,
        )

        TipoAtendimentoEncaixe.objects.bulk_create([
            TipoAtendimentoEncaixe(encaixe=encaixe, tipo=t)
            for t in cleaned_data.get("tipos_atendimento", [])
        ])

    return encaixe
