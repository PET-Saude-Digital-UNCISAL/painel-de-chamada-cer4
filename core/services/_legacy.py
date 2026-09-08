"""Application services for isolated screen rendering.

 

Humble Object approach:

- Views call these functions and only render context.

- Business/data assembly lives here.

"""



from base64 import b64encode

from calendar import monthrange

from dataclasses import dataclass

from datetime import date, datetime, timedelta

from functools import lru_cache

from mimetypes import guess_type

from pathlib import Path

from typing import Optional



from django.urls import reverse

from django.utils import timezone



from core.clock import SystemClock

from core.models import EncaixePaciente, Paciente, TipoAtendimentoEncaixe
from core.websocket_utils import notificar_fila_atualizada, notificar_pacientes_em_espera





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
    ScreenDefinition("perdeu-chamada", "Senha Perdida (Perdeu Chamada)", "Daniely Vasconcelos", "concluída"),

    ScreenDefinition(

        "auditoria-percurso-seguranca",

        "Auditoria de Percurso e Segurança",

        "Daniely Vasconcelos",

        "em desenvolvimento",

    ),

]





# NOTA: este arquivo (core/services/_legacy.py) mora um nivel mais fundo
# do que o antigo core/services.py -- por isso .parent.parent (nao so
# .parent) pra chegar em core/, onde fica static/. Se essas constantes
# forem movidas pra outro modulo do pacote no futuro, reconferir quantos
# ".parent" sao necessarios a partir do novo caminho.
PAINEL_CHAMADA_ASSETS_DIR = Path(__file__).resolve().parent.parent / "static" / "core" / "painel_chamada" / "assets"





@lru_cache

def _get_painel_chamada_asset_data_url(relative_path: str) -> str:

    asset_path = PAINEL_CHAMADA_ASSETS_DIR / relative_path

    content_type = guess_type(asset_path.name)[0] or "application/octet-stream"

    encoded_content = b64encode(asset_path.read_bytes()).decode("ascii")

    return f"data:{content_type};base64,{encoded_content}"





@dataclass(frozen=True)
class _PainelChamadaDados:
    hoje: date
    agora: datetime
    dias_pt: list
    meses_pt: list
    ultimo: Optional[EncaixePaciente]
    chamados_hoje: list


def _carregar_dados_painel() -> _PainelChamadaDados:
    from django.utils import timezone
    hoje = timezone.localdate()
    agora = timezone.localtime()
    dias_pt = ["SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA", "SEXTA-FEIRA", "SÁBADO", "DOMINGO"]
    meses_pt = ["", "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
    ultimo = (
        EncaixePaciente.objects.filter(
            data_atendimento=hoje,
            status__in=[EncaixePaciente.Status.ATENDIMENTO, EncaixePaciente.Status.CHAMADO],
        )
        .order_by("-chamado_em")
        .first()
    )
    if not ultimo:
        ultimo = EncaixePaciente.objects.filter(data_atendimento=hoje).order_by("-criado_em").first()
    chamados_hoje = list(
        EncaixePaciente.objects.filter(data_atendimento=hoje, chamado_em__isnull=False)
        .order_by("-chamado_em")[:5]
    )
    return _PainelChamadaDados(hoje, agora, dias_pt, meses_pt, ultimo, chamados_hoje)


def get_painel_chamada_context(use_real_data: bool = False) -> dict:

    if use_real_data:
        d = _carregar_dados_painel()

    return {

        "page_title": "Painel de Chamada",

        "reception_name": "RECEPÇÃO 3",

        "weekday": f"{d.dias_pt[d.hoje.weekday()]}," if use_real_data else "SEGUNDA-FEIRA,",

        "current_date": f"{d.hoje.day:02d} DE {d.meses_pt[d.hoje.month]} DE {d.hoje.year}" if use_real_data else "27 DE ABRIL DE 2026",

        "current_time": d.agora.strftime("%H:%M") if use_real_data else "10:48",

        "current_call": (
            {
                "ticket": d.ultimo.senha,
                "patient_name": d.ultimo.nome_completo.upper(),
                "room": d.ultimo.sala.upper() if d.ultimo.sala else "SALA 01",
                "service_type": (
                    list(d.ultimo.tipos_atendimento.all())[0].get_tipo_display().upper()
                    if d.ultimo and d.ultimo.tipos_atendimento.exists()
                    else "AMBULATORIAL"
                ),
            }
            if use_real_data and d.ultimo
            else (
                {
                    "ticket": "---",
                    "patient_name": "---",
                    "room": "---",
                    "service_type": "---",
                }
                if use_real_data
                else {
                    "ticket": "A011",
                    "patient_name": "FELIPE DA SILVA",
                    "room": "SALA 04",
                    "service_type": "AMBULATORIAL",
                }
            )
        ),

        "recent_calls": (
            [
                {
                    "ticket": e.senha,
                    "room": e.sala.upper() if e.sala else "SALA 01",
                    "patient_name": e.nome_completo.upper(),
                    "time": e.chamado_em.strftime("%H:%M") if e.chamado_em else "--:--",
                }
                for e in d.chamados_hoje
            ]
            if use_real_data
            else [
                {"ticket": "A010", "room": "SALA 02", "patient_name": "MARIA DA SILVA", "time": "10:48"},
                {"ticket": "B005", "room": "SALA 03", "patient_name": "MARIA JOSÉ", "time": "10:48"},
                {"ticket": "A009", "room": "SALA 06", "patient_name": "ABRAÃO FARIAS DE LIMA", "time": "10:48"},
                {"ticket": "A008", "room": "SALA 05", "patient_name": "JOÃO PEDRO MIGUEL", "time": "10:48"},
                {"ticket": "A007", "room": "SALA 01", "patient_name": "LUCAS FERREIRA", "time": "10:48"},
            ]
        ),

        "notice_items": [
            "DIRIJA-SE À SUA SALA AO SER CHAMADO",
            "FIQUE ATENTO AO SINAL SONORO DA CHAMADA",
            "RESPEITE A ORDEM DAS FILAS",
            (
                f"HOJE É {d.dias_pt[d.hoje.weekday()]}, {d.hoje.day:02d} DE {d.meses_pt[d.hoje.month]} DE {d.hoje.year}"
                if use_real_data
                else "HOJE É SEGUNDA-FEIRA, 27 DE ABRIL DE 2026"
            ),
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





# Mesma observacao de PAINEL_CHAMADA_ASSETS_DIR acima sobre o .parent.parent.
PACIENTE_CHAMADO_ASSETS_DIR = Path(__file__).resolve().parent.parent / "static" / "core" / "paciente_chamado" / "assets"





@lru_cache

def _get_paciente_chamado_asset_data_url(relative_path: str) -> str:

    asset_path = PACIENTE_CHAMADO_ASSETS_DIR / relative_path

    content_type = guess_type(asset_path.name)[0] or "application/octet-stream"

    encoded_content = b64encode(asset_path.read_bytes()).decode("ascii")

    return f"data:{content_type};base64,{encoded_content}"





def resolver_encaixe_da_sessao(request, *, permitir_fallback_por_senha=False):
    """Resolve o EncaixePaciente do paciente identificado pela sessao atual.

    Centraliza uma logica que estava duplicada (com pequenas variacoes, e em
    um dos casos com um bug real de vazamento de dados) em varias views do
    fluxo mobile do paciente. A regra de ouro aqui e: se a sessao sabe quem
    e o paciente, o retorno tem que ser um encaixe DESSE paciente -- nunca
    de outro, mesmo que a busca "nao ache nada bonito" e a gente tenha que
    devolver None.

    Ordem de resolucao:
    1. `encaixe_id` da sessao, mas so e aceito se pertencer ao paciente da
       sessao (quando ele existir). Isso evita usar um `encaixe_id` "velho",
       de uma sessao anterior, num dispositivo compartilhado por varios
       pacientes ao longo do dia.
    2. Se nao achou por `encaixe_id`, busca pelo CPF do paciente da sessao,
       filtrando por hoje. Quando o paciente tem mais de um encaixe no
       mesmo dia (ex.: dois tipos de atendimento), prioriza o que esta
       CHAMADO ou em ATENDIMENTO agora -- nao simplesmente "o mais recente
       criado", que pode nao ser o que acabou de ser chamado.
    3. So quando NENHUMA identidade de sessao existir (nem `paciente_id`
       nem `encaixe_id`) e que aceitamos `?senha=` da querystring como
       identificacao de reserva -- e mesmo assim, so se quem chamou passou
       `permitir_fallback_por_senha=True`. Esse fallback existe para o caso
       de a sessao ter se perdido entre o redirect disparado por
       WebSocket/polling e a pagina realmente carregar; ele nunca pode
       substituir uma sessao de paciente que ja existe.

    Retorna `None` quando nada e encontrado -- cabe a view decidir o que
    fazer nesse caso (normalmente renderizar um contexto mockado/generico).
    """
    encaixe_id = request.session.get("encaixe_id")
    paciente_id = request.session.get("paciente_id")

    paciente_sessao = Paciente.objects.filter(pk=paciente_id).first() if paciente_id else None

    encaixe = None
    if encaixe_id:
        candidato = EncaixePaciente.objects.filter(pk=encaixe_id).first()
        # Um `encaixe_id` na sessao so vale se for do mesmo paciente que a
        # sessao diz ser dona dela. Sem essa checagem, um `encaixe_id`
        # desatualizado (sessao reaproveitada em outro atendimento) faria a
        # view mostrar o encaixe de outra pessoa.
        if candidato and (not paciente_sessao or candidato.cpf == paciente_sessao.cpf):
            encaixe = candidato

    if not encaixe and paciente_sessao:
        candidatos_hoje = EncaixePaciente.objects.filter(
            cpf=paciente_sessao.cpf, data_atendimento=timezone.localdate(),
        )
        # Entre os encaixes de hoje do paciente, o que esta chamado ou em
        # atendimento tem prioridade sobre "o mais recente criado" -- que
        # nao e necessariamente o encaixe ativo no momento.
        encaixe = (
            candidatos_hoje.filter(
                status__in=[EncaixePaciente.Status.CHAMADO, EncaixePaciente.Status.ATENDIMENTO],
            ).order_by("-chamado_em").first()
            or candidatos_hoje.order_by("-criado_em").first()
        )

    if permitir_fallback_por_senha and not encaixe and not paciente_sessao and not encaixe_id:
        # Ultima reserva, e so quando nao ha NENHUMA identidade de sessao:
        # trata a senha da querystring como identificacao de quem abriu o
        # link. Isso nunca compete com uma sessao de paciente ja existente
        # -- se ela existir e simplesmente nao tiver achado um encaixe
        # ativo, caimos em None (a view mostra um contexto generico) em vez
        # de arriscar exibir dados de outra pessoa.
        senha_param = request.GET.get("senha", "").strip().upper()
        if senha_param:
            encaixe = EncaixePaciente.objects.filter(
                senha=senha_param, data_atendimento=timezone.localdate(),
            ).order_by("-criado_em").first()

    return encaixe


def get_paciente_chamado_context() -> dict:

    return {

        "page_title": "Paciente Chamado",

        "title": "PACIENTE CHAMADO",

        "subtitle": "Dirija-se ao local indicado para atendimento",

        "senha": "A012",

        "paciente": "Ricardo Augusto Oliveira",

        "sala": "10",

        "cpf": "",

        "tipo_atendimento": "Ambulatorial",

        "status": "Chamada atual",

        "mensagem": "Se precisar de ajuda, procure a recepção.",

        "footer_indicators": [

            {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

            {"label": "Conexão", "detail": "Segura", "icon": "shield"},

        ],

        "public_sans_font_url": _get_paciente_chamado_asset_data_url("public-sans.ttf"),

        "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),

    }





def get_acompanhamento_atendimento_context() -> dict:

    """Return the mocked payload for the patient's queue tracking screen."""

    return {

        "page_title": "Acompanhamento de Atendimento",

        "title": "Acompanhamento de Atendimento",

        "title_line_1": "Acompanhamento de",

        "title_line_2": "Atendimento",

        "subtitle": "Confira sua posição atual na fila",

        "paciente": "Ricardo Augusto Oliveira",

        "senha": "A012",
        "cpf": "000.000.000-00",

        "sala_prevista": "Sala 10",

        "tipo_atendimento": "Ambulatorial",

        "chamando_agora": "A001",

        "pacientes_a_frente": 2,

        "mensagem": "Permaneça atento ao painel de chamadas e aguarde sua vez.",

        "footer_indicators": [

            {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

            {"label": "Conexão", "detail": "Segura", "icon": "shield"},

        ],

        "public_sans_font_url": _get_paciente_chamado_asset_data_url("public-sans.ttf"),

        "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),

    }





def get_checkin_concluido_context() -> dict:

    """Return the mocked payload for the completed check-in screen."""

    return {

        "page_title": "Check-in concluído",

        "title": "Check-in concluído",

        "subtitle": "Você já está na fila de atendimento",

        "paciente": "Ricardo Augusto Oliveira",

        "senha": "A012",

        "mensagem": "Acompanhe sua posição na fila e aguarde sua chamada.",

        "texto_botao": "Acompanhar fila",

        "footer_indicators": [

            {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

            {"label": "Conexão", "detail": "Segura", "icon": "shield"},

        ],

        "public_sans_font_url": _get_paciente_chamado_asset_data_url("public-sans.ttf"),

        "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),

    }





def get_checkin_assistido_context() -> dict:

    """Return the mocked payload for the assisted check-in guidance screen."""

    return {

        "page_title": "Check-in Assistido",

        "title": "Siga para a Recepção",

        "message": (

            "Nossa equipe no balcão principal ajudará com seu check-in. "

            "Por favor, tenha um documento com foto em mãos."

        ),

        "footer_indicators": [

            {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

            {"label": "Conexão", "detail": "Segura", "icon": "shield"},

        ],

        "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),

    }





def get_bloqueio_direcionamento_context() -> dict:

    """Return the mocked payload for the in-person confirmation screen."""

    return {

        "page_title": "Bloqueio e Direcionamento para Recepção",

        "title": "Confirmação presencial necessária",

        "title_line_1": "Confirmação presencial",

        "title_line_2": "necessária",

        "subtitle": (

            "Seus dados foram encontrados, mas seu atendimento precisa de "

            "confirmação presencial."

        ),

        "next_step_label": "PRÓXIMO PASSO",

        "next_step_title": "Dirija-se à recepção",

        "next_step_description": (

            "A equipe confirmará seus dados e orientará os próximos passos."

        ),

        "location_label": "Local",

        "location": "Balcão da recepção",

        "info_message": (

            "Seu atendimento continuará após a confirmação na recepção."

        ),

        "status": "Confirmação na recepção",

        "review_label": "Revisar meus dados",

        "footer_indicators": [

            {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

            {"label": "Conexão", "detail": "Segura", "icon": "shield"},

        ],

        "cer_logo_url": _get_painel_chamada_asset_data_url("logo-cer.svg"),

        "public_sans_font_url": _get_paciente_chamado_asset_data_url("public-sans.ttf"),

        "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),

    }





def get_identificacao_paciente_context() -> dict:

    """Return the mocked payload for the patient identification screen."""

    return {

        "page_title": "Identificação do Paciente",

        "title": "Bem-vindo",

        "subtitle": "Digite seus dados para iniciar o atendimento",

        "fields": [

            {

                "name": "cpf",

                "label": "CPF",

                "placeholder": "000.000.000-00",

                "inputmode": "numeric",

                "autocomplete": "off",

                "icon": "document",

            },

            {

                "name": "data_nascimento",

                "label": "Data de nascimento",

                "placeholder": "DD/MM/AAAA",

                "inputmode": "numeric",

                "autocomplete": "bday",

                "icon": "calendar",

            },

            {

                "name": "nome_mae",

                "label": "Nome da mãe",

                "placeholder": "Digite o nome completo",

                "inputmode": "text",

                "autocomplete": "off",

                "icon": "person",

            },

        ],

        "texto_botao_principal": "Realizar Check-in",

        "texto_botao_assistido": "Preciso de ajuda",

        "validation_title": "Validando dados...",

        "validation_detail": "Conexão segura",

        "footer_indicators": [

            {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

            {"label": "Conexão", "detail": "Segura", "icon": "shield"},

        ],

        "cer_logo_url": _get_painel_chamada_asset_data_url("logo-cer.svg"),

        "public_sans_font_url": _get_paciente_chamado_asset_data_url("public-sans.ttf"),

        "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),

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

    return "".join(ch for ch in value if ch.isdigit())





def _parse_iso_date(value: str) -> Optional[date]:

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


def registrar_encaixe(cleaned_data: dict, arquivo=None) -> EncaixePaciente:

    """Gera senha, calcula posição e persiste o encaixe no banco."""

    from django.db import transaction



    hoje = timezone.localdate()



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

            origem=EncaixePaciente.Origem.ENCAIXE,

        )



        TipoAtendimentoEncaixe.objects.bulk_create([

            TipoAtendimentoEncaixe(encaixe=encaixe, tipo=t)

            for t in cleaned_data.get("tipos_atendimento", [])

        ])



    notificar_fila_atualizada()

    return encaixe





def _normalizar_nome(nome: str) -> str:
    return " ".join((nome or "").strip().split()).casefold()


def identidade_confere(paciente, data_nasc, nome_mae) -> bool:
    """Confere a Data de Nascimento e o Nome da Mãe informados no check-in
    contra o cadastro do ``paciente``.

    O CPF sozinho não é suficiente para autenticar o check-in: qualquer
    pessoa que soubesse o CPF (documento não é secreto) conseguiria se
    passar por outro paciente. Por isso, quando o cadastro do paciente já
    possui a data de nascimento e/ou o nome da mãe preenchidos, esses
    valores viram obrigatórios e precisam bater com o que foi digitado.

    Quando o cadastro não tem essa informação preenchida (ex.: paciente que
    se auto-cadastrou pelo app e não informou nome da mãe), não há o que
    conferir para aquele campo e ele é ignorado — não é uma falha de
    segurança nova, é uma limitação de dados pré-existente.
    """
    if paciente.data_nascimento:
        if not data_nasc or data_nasc != paciente.data_nascimento:
            return False

    if paciente.nome_mae:
        if not nome_mae or _normalizar_nome(nome_mae) != _normalizar_nome(paciente.nome_mae):
            return False

    return True


def registrar_checkin(paciente, data_nasc, nome_mae) -> EncaixePaciente | None:

    """Realiza check-in de paciente com agendamento prévio para hoje."""

    from django.db import transaction



    from django.utils import timezone

    from core.models import Agendamento, TipoAtendimentoEncaixe



    hoje = timezone.localdate()



    # Paciente que já fez check-in hoje (e saiu do app/fechou o navegador, por
    # exemplo) não deve gerar um novo encaixe/senha ao reenviar os dados — só
    # retorna o encaixe já existente. Isso também cobre o caso em que o
    # Agendamento de hoje já foi marcado como CHECKIN_REALIZADO pelo primeiro
    # check-in, então essa checagem precisa vir antes do filtro por AGENDADO.
    encaixe_existente = (
        EncaixePaciente.objects.filter(cpf=paciente.cpf, data_atendimento=hoje)
        .order_by("-criado_em")
        .first()
    )

    if encaixe_existente:

        return encaixe_existente



    agendamento = Agendamento.objects.filter(

        paciente=paciente,

        data_agendamento=hoje,

        status=Agendamento.Status.AGENDADO,

    ).first()



    if not agendamento:

        return None


    with transaction.atomic():

        ultimo = (

            EncaixePaciente.objects.filter(data_atendimento=hoje)

            .order_by("-posicao_fila")

            .first()

        )

        proxima_posicao = (ultimo.posicao_fila + 1) if ultimo else 1

        senha = f"E{proxima_posicao:03d}"



        encaixe = EncaixePaciente.objects.create(

            nome_completo=paciente.nome_completo,

            cpf=paciente.cpf,

            data_nascimento=data_nasc or paciente.data_nascimento,

            nome_mae=nome_mae or paciente.nome_mae,

            justificativa="",

            senha=senha,

            posicao_fila=proxima_posicao,

            data_atendimento=hoje,

            status=EncaixePaciente.Status.AGUARDANDO,

            origem=EncaixePaciente.Origem.CHECKIN,

        )



        TipoAtendimentoEncaixe.objects.create(

            encaixe=encaixe,

            tipo=agendamento.tipo_atendimento,

        )



        agendamento.status = Agendamento.Status.CHECKIN_REALIZADO

        agendamento.save(update_fields=["status"])



    # Só avisa quem já está esperando sobre a posição na fila — o check-in é
    # iniciado pelo próprio paciente no Mobile, não pelo módulo Atendimentos
    # do Dia, então não deve acionar o Painel de Chamada.
    notificar_pacientes_em_espera()

    return encaixe







