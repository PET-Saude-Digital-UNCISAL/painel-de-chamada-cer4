"""Dominio de encaixe: registro do paciente que chega sem agendamento previo.

Segunda fatia da divisao por dominio da Fase 3 (a primeira foi
autenticacao, em core/services/autenticacao.py). registrar_encaixe e a
unica funcao de servico usada exclusivamente pelas views de encaixe
(core/views/encaixe.py) -- identidade_confere e registrar_checkin, que
tambem mexem em EncaixePaciente, ficam em _legacy.py porque pertencem ao
fluxo de check-in do paciente (proxima fatia), nao ao de encaixe.
"""

from django.utils import timezone

from core.models import EncaixePaciente, TipoAtendimentoEncaixe
from core.websocket_utils import notificar_fila_atualizada


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
