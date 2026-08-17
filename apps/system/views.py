from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import EncaixePaciente
from core.websocket_utils import notificar_painel_chamada, notificar_fila_atualizada, notificar_paciente
from core.auth_decorators import permissao_requerida


@require_POST
@permissao_requerida("checkin")
def chamar_paciente_view(request):
    senha = request.POST.get("senha", "")
    sala = request.POST.get("sala", "Sala 1")
    guiche = request.POST.get("guiche", "")

    with transaction.atomic():
        encaixe = get_object_or_404(
            EncaixePaciente,
            senha=senha,
            data_atendimento=timezone.localdate(),
        )

        if encaixe.status not in (
            EncaixePaciente.Status.AGUARDANDO,
            EncaixePaciente.Status.AUSENTE,
        ):
            return JsonResponse(
                {"ok": False, "erro": "Paciente não está aguardando na fila"},
                status=409,
            )

        is_rechamada = encaixe.status == EncaixePaciente.Status.AUSENTE
        encaixe.status = EncaixePaciente.Status.CHAMADO
        encaixe.sala = sala
        encaixe.chamado_em = timezone.now()
        if is_rechamada:
            encaixe.vezes_chamado += 1
        encaixe.save(update_fields=["status", "sala", "chamado_em", "vezes_chamado"])

    notificar_painel_chamada(encaixe, sala, guiche)
    notificar_fila_atualizada()
    notificar_paciente(
        encaixe.cpf,
        "paciente_chamado",
        senha=encaixe.senha,
        nome=encaixe.nome_completo,
        sala=sala,
        guiche=guiche,
        timestamp=timezone.now().isoformat(),
    )

    return JsonResponse({"ok": True, "senha": encaixe.senha, "rechamada": is_rechamada})


@require_POST
@permissao_requerida("checkin")
def marcar_ausente_view(request):
    senha = request.POST.get("senha", "")

    with transaction.atomic():
        encaixe = get_object_or_404(
            EncaixePaciente,
            senha=senha,
            data_atendimento=timezone.localdate(),
        )

        if encaixe.status not in (
            EncaixePaciente.Status.CHAMADO,
            EncaixePaciente.Status.ATENDIMENTO,
        ):
            return JsonResponse(
                {"ok": False, "erro": "Paciente precisa estar chamado ou em atendimento"},
                status=400,
            )

        encaixe.status = EncaixePaciente.Status.AUSENTE
        encaixe.ausente_em = timezone.now()
        encaixe.vezes_chamado += 1
        encaixe.save(update_fields=["status", "ausente_em", "vezes_chamado"])

    notificar_fila_atualizada()
    notificar_paciente(
        encaixe.cpf,
        "paciente_ausente",
        senha=encaixe.senha,
        nome=encaixe.nome_completo,
        timestamp=timezone.now().isoformat(),
    )

    return JsonResponse({"ok": True, "senha": encaixe.senha})
