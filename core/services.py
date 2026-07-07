"""Application services for isolated screen rendering.
 
Humble Object approach:
- Views call these functions and only render context.
- Business/data assembly lives here.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from core.clock import SystemClock


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
    ScreenDefinition("dev6", "Tela de Configurações", "Dev 6", "em desenvolvimento"),
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
 
 
def list_team_screens() -> list[dict]:
    """Return cards used by the dashboard and direct route links."""
    # Agrupando telas relacionadas a Pacientes
    pacientes_group = {
        "is_group": True,
        "title": "Telas de Pacientes",
        "owner": "Devs 1, 2, 3",
        "status": "em desenvolvimento",
        "screens": [
            {
                "slug": "pacientes-listagem",
                "title": "01: Listagem de Pacientes",
                "owner": "Dev 1",
                "status": "em desenvolvimento",
                "path": "/telas/pacientes-listagem/",
            },
            {
                "slug": "perdeu-chamada",
                "title": "02: Senha Perdida",
                "owner": "Daniely Vasconcelos",
                "status": "concluída",
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
    """Apply audit filters over PostgreSQL data or mocks.

    In the isolated dev environment we filter mock data.
    """
    termo = (filtros_dict.get("q") or "").strip().lower()
    termo_digitos = _only_digits(termo)
    data_inicio, data_fim = _resolve_auditoria_date_range(filtros_dict)
    setor_filtro = (filtros_dict.get("setor") or "").strip()
    status_filtro = (filtros_dict.get("status") or "").strip().upper()
    apenas_alertas = str(filtros_dict.get("apenas_alertas") or "").lower() in {"1", "true", "on", "yes"}

    pacientes_filtrados = []
    for paciente in AUDITORIA_MOCK_DATA:
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
        "page_title": "CER III — Auditoria de Percurso e Segurança",
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
