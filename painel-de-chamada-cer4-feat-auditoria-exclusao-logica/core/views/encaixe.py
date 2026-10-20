"""Views do dominio de encaixe: paciente sem agendamento previo entra na
fila (encaixe_view) e o fluxo de atendimento dele e conduzido pela recepcao
(validar/iniciar/concluir). Segunda fatia da divisao por dominio da Fase 3.
"""

from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from core.forms import EncaixeForm
from core.models import EncaixePaciente
from core.websocket_utils import notificar_fila_atualizada, notificar_paciente
from core.auth_decorators import permissao_requerida
from core.services import registrar_encaixe


@require_POST

def encaixe_view(request):

    """Recebe o formulário de encaixe, persiste e retorna JSON com a senha gerada."""

    form = EncaixeForm(request.POST, request.FILES)

    if form.is_valid():

        try:

            encaixe = registrar_encaixe(form.cleaned_data, arquivo=request.FILES.get("anexo"))

            return JsonResponse({"ok": True, "senha": encaixe.senha, "posicao": encaixe.posicao_fila})

        except Exception as e:

            return JsonResponse({"ok": False, "erros": {"__all__": [str(e)]}}, status=500)



    return JsonResponse({"ok": False, "erros": form.errors}, status=400)


@require_POST

@permissao_requerida("checkin")

def validar_encaixe_view(request, encaixe_id):

    """Transiciona VALIDACAO â†’ AGUARDANDO."""

    encaixe = get_object_or_404(EncaixePaciente, pk=encaixe_id)

    if encaixe.status != EncaixePaciente.Status.VALIDACAO:

        return JsonResponse({"ok": False, "erro": "Status inválido para validação."}, status=400)

    encaixe.status = EncaixePaciente.Status.AGUARDANDO

    encaixe.save(update_fields=["status"])

    notificar_fila_atualizada()

    return JsonResponse({"ok": True})


@require_POST

@permissao_requerida("checkin")

def iniciar_atendimento_view(request, encaixe_id):

    """Transiciona CHAMADO â†’ ATENDIMENTO."""

    encaixe = get_object_or_404(EncaixePaciente, pk=encaixe_id)

    if encaixe.status != EncaixePaciente.Status.CHAMADO:

        return JsonResponse({"ok": False, "erro": "Paciente não foi chamado."}, status=400)

    encaixe.status = EncaixePaciente.Status.ATENDIMENTO

    encaixe.save(update_fields=["status"])

    notificar_fila_atualizada()
    notificar_paciente(
        encaixe.cpf,
        "paciente_atendimento",
        senha=encaixe.senha,
        nome=encaixe.nome_completo,
        sala=encaixe.sala,
        timestamp=timezone.now().isoformat(),
    )

    return JsonResponse({"ok": True})


@require_POST

@permissao_requerida("checkin")

def concluir_atendimento_view(request, encaixe_id):

    """Transiciona ATENDIMENTO â†’ CONCLUIDO."""

    encaixe = get_object_or_404(EncaixePaciente, pk=encaixe_id)

    if encaixe.status != EncaixePaciente.Status.ATENDIMENTO:

        return JsonResponse({"ok": False, "erro": "Atendimento nÃ£o estÃ¡ em andamento."}, status=400)
    encaixe.status = EncaixePaciente.Status.CONCLUIDO
    encaixe.concluido_em = timezone.now()

    encaixe.save(update_fields=["status", "concluido_em"])

    notificar_fila_atualizada()
    notificar_paciente(
        encaixe.cpf,
        "paciente_concluido",
        senha=encaixe.senha,
        nome=encaixe.nome_completo,
        timestamp=timezone.now().isoformat(),
    )

    from django.conf import settings
    from core.integrador import IntegradorHttp

    base_url = getattr(settings, "INTEGRADOR_BASE_URL", "")
    if base_url:
        token = getattr(settings, "INTEGRADOR_TOKEN", "")
        integrador = IntegradorHttp(base_url=base_url, token=token)
        integrador.notificar_conclusao(encaixe)

    return JsonResponse({

        "ok": True,

        "redirect_url": f"/pesquisa-satisfacao/?cpf={encaixe.cpf}",

    })
