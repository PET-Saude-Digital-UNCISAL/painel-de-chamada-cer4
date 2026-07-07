"""Application services for isolated screen rendering.
 
Humble Object approach:
- Views call these functions and only render context.
- Business/data assembly lives here.
"""

from dataclasses import dataclass
from typing import Optional
 
 
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
