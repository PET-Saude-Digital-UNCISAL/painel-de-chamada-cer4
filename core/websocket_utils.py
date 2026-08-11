from datetime import datetime
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from core.models import EncaixePaciente


def _group_send(group_name, event_type, **kwargs):
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": event_type, **kwargs},
        )
    except Exception:
        import logging
        logging.exception("Falha ao enviar WebSocket para grupo %s", group_name)


def notificar_painel_chamada(encaixe, sala, guiche=""):
    _group_send(
        "painel_chamada",
        "paciente_chamado",
        senha=encaixe.senha,
        nome=encaixe.nome_completo,
        sala=sala,
        guiche=guiche,
        timestamp=datetime.now().isoformat(),
    )


def notificar_fila_atualizada():
    """Avisa o Painel de Chamada e os pacientes que estão esperando que a
    fila mudou.

    Só deve ser chamada por ações do módulo Atendimentos do Dia (chamar,
    marcar ausente, validar, iniciar/concluir atendimento, encaixe) — é o
    que atualiza o grupo `painel_chamada`. Fluxos disparados pelo próprio
    paciente no Mobile (ex.: check-in) devem chamar
    `notificar_pacientes_em_espera()` diretamente, sem tocar no Painel.
    """
    from datetime import date
    hoje = date.today()
    _notificar_painel(hoje)
    notificar_pacientes_em_espera(hoje)


def _notificar_painel(hoje):
    fila = list(
        EncaixePaciente.objects.filter(
            data_atendimento=hoje,
            status__in=[
                EncaixePaciente.Status.AGUARDANDO,
                EncaixePaciente.Status.CHAMADO,
                EncaixePaciente.Status.ATENDIMENTO,
            ],
        )
        .order_by("posicao_fila")
        .values("senha", "nome_completo", "posicao_fila", "status", "sala")
    )
    chamados_hoje = list(
        EncaixePaciente.objects.filter(
            data_atendimento=hoje,
            chamado_em__isnull=False,
        )
        .order_by("-chamado_em")
        .values("senha", "nome_completo", "sala", "chamado_em")[:10]
    )
    recent_calls = [
        {
            "ticket": c["senha"],
            "room": (c["sala"] or "SALA 01").upper(),
            "patient_name": c["nome_completo"].upper(),
            "time": c["chamado_em"].strftime("%H:%M") if c["chamado_em"] else "--:--",
        }
        for c in chamados_hoje
    ]
    _group_send(
        "painel_chamada",
        "fila_atualizada",
        fila=fila,
        recent_calls=recent_calls,
        timestamp=datetime.now().isoformat(),
    )


def notificar_pacientes_em_espera(hoje=None):
    """Envia, via WebSocket, a posição atualizada na fila para cada paciente
    aguardando/em validação (grupo `paciente_{cpf}`) — sem tocar no Painel
    de Chamada.

    Usada tanto pelo módulo Atendimentos do Dia (via `notificar_fila_atualizada`)
    quanto diretamente pelo check-in do paciente no Mobile, que precisa
    avisar quem já está na fila sobre a nova posição, mas não deve acionar
    o Painel (esse gatilho é exclusivo do Atendimentos do Dia).

    Sem isso o app mobile só descobre mudanças de posição no próximo ciclo
    do polling de 5s, em vez de em tempo real.
    """
    from datetime import date
    if hoje is None:
        hoje = date.today()
    chamando = (
        EncaixePaciente.objects.filter(
            data_atendimento=hoje,
            status__in=[EncaixePaciente.Status.CHAMADO, EncaixePaciente.Status.ATENDIMENTO],
        )
        .order_by("-chamado_em")
        .first()
    )
    chamando_senha = chamando.senha if chamando else None

    em_espera = list(
        EncaixePaciente.objects.filter(
            data_atendimento=hoje,
            status__in=[EncaixePaciente.Status.AGUARDANDO, EncaixePaciente.Status.VALIDACAO],
        )
        .order_by("posicao_fila")
        .values("cpf", "senha")
    )

    timestamp = datetime.now().isoformat()
    for pacientes_a_frente, paciente in enumerate(em_espera):
        if not paciente["cpf"]:
            continue
        _group_send(
            f"paciente_{paciente['cpf']}",
            "fila_atualizada",
            chamando_agora=chamando_senha,
            senha=paciente["senha"],
            pacientes_a_frente=pacientes_a_frente,
            timestamp=timestamp,
        )


def notificar_paciente(cpf, event_type, **kwargs):
    if not cpf:
        return
    _group_send(
        f"paciente_{cpf}",
        event_type,
        **kwargs,
    )
