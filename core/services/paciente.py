"""Dominio do paciente: contextos das telas mobile (painel de chamada,
chamada individual, acompanhamento, checkin) e a logica de identidade e
checkin que alimenta identificacao_paciente_view e fluxo_paciente_view.
Terceira fatia da divisao por dominio da Fase 3.
"""

from base64 import b64encode
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from mimetypes import guess_type
from pathlib import Path
from typing import Optional

from django.utils import timezone

from core.models import EncaixePaciente, Paciente
from core.websocket_utils import notificar_pacientes_em_espera


# NOTA: este arquivo (core/services/paciente.py) mora um nivel mais fundo
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
