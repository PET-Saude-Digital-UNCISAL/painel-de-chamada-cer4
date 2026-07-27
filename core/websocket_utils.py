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
        "paciente.chamado",
        senha=encaixe.senha,
        nome=encaixe.nome_completo,
        sala=sala,
        guiche=guiche,
        timestamp=datetime.now().isoformat(),
    )


def notificar_fila_atualizada():
    from datetime import date
    hoje = date.today()
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
        "fila.atualizada",
        fila=fila,
        recent_calls=recent_calls,
        timestamp=datetime.now().isoformat(),
    )


def notificar_paciente(cpf, event_type, **kwargs):
    if not cpf:
        return
    _group_send(
        f"paciente_{cpf}",
        event_type,
        **kwargs,
    )
