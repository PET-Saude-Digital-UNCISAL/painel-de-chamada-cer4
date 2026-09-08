"""Views do dominio do paciente: o fluxo mobile completo, do primeiro
identificacao ate ser chamado e atendido (painel de chamada, chamada
individual, acompanhamento, checkin, bloqueios e navegacao entre telas).
Terceira fatia da divisao por dominio da Fase 3 -- a maior ate aqui.
"""

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods

from core.forms import IdentificacaoForm
from core.models import EncaixePaciente, Paciente
from core.services import (
    _get_painel_chamada_asset_data_url,
    get_acompanhamento_atendimento_context,
    get_bloqueio_direcionamento_context,
    get_checkin_assistido_context,
    get_checkin_concluido_context,
    get_identificacao_paciente_context,
    get_paciente_chamado_context,
    get_painel_chamada_context,
    identidade_confere,
    list_patient_screens,
    registrar_checkin,
    resolver_encaixe_da_sessao,
)


@xframe_options_sameorigin

def painel_chamada_view(request):

    """Tela de TV do Painel de Chamada -- so renderiza o contexto com
    dados reais do banco (use_real_data=True); a atualizacao em tempo
    real depois disso e toda via WebSocket, ver painel_chamada.html."""

    context = get_painel_chamada_context(use_real_data=True)

    return render(request, "display/painel_chamada.html", context)


@xframe_options_sameorigin
def paciente_chamado_view(request):
    """Renderiza a tela de "paciente chamado".

    A resolução do encaixe é centralizada em `resolver_encaixe_da_sessao`
    (core/services.py) — mesma função usada pelas demais telas do fluxo do
    paciente. Aqui ela é chamada com `permitir_fallback_por_senha=True`
    porque é para esta tela que o WebSocket/polling redireciona o paciente
    quando ele é chamado, e a sessão pode eventualmente ter se perdido
    nesse meio-tempo (ver a docstring da função para os detalhes de quando
    esse fallback entra em ação — ele nunca compete com uma sessão válida).
    """
    encaixe = resolver_encaixe_da_sessao(request, permitir_fallback_por_senha=True)

    if encaixe:
        if encaixe.status not in (
            EncaixePaciente.Status.CHAMADO,
            EncaixePaciente.Status.ATENDIMENTO,
        ):
            return redirect("acompanhamento-atendimento")

        tipos = list(encaixe.tipos_atendimento.all())

        context = {
            "page_title": "Paciente Chamado",
            "title": "PACIENTE CHAMADO",
            "subtitle": "Dirija-se ao local indicado para atendimento",
            "senha": encaixe.senha,
            "paciente": encaixe.nome_completo,
            "sala": encaixe.sala or "Sala 10",
            "cpf": encaixe.cpf,
            "tipo_atendimento": tipos[0].get_tipo_display() if tipos else "Ambulatorial",
            "status": "Chamada atual",
            "mensagem": "Se precisar de ajuda, procure a recepção.",
            "footer_indicators": [
                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},
                {"label": "Conexão", "detail": "Segura", "icon": "shield"},
            ],
            "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),
        }
        return render(request, "mobile/paciente_chamado.html", context)

    return render(request, "mobile/paciente_chamado.html", get_paciente_chamado_context())


@xframe_options_sameorigin

def acompanhamento_atendimento_view(request):
    # Mesma resolução de sessão usada em todo o fluxo do paciente (ver
    # resolver_encaixe_da_sessao em core/services.py). Não há motivo para
    # aceitar `?senha=` como identificação de reserva aqui — quem chega
    # nesta tela normalmente já veio de um check-in com sessão válida.
    encaixe = resolver_encaixe_da_sessao(request)

    if encaixe:

        pacientes_a_frente = EncaixePaciente.objects.filter(
            data_atendimento=encaixe.data_atendimento,
            status__in=[EncaixePaciente.Status.AGUARDANDO, EncaixePaciente.Status.VALIDACAO],
            posicao_fila__lt=encaixe.posicao_fila,
        ).count()

        chamando_agora = EncaixePaciente.objects.filter(

            data_atendimento=encaixe.data_atendimento,

            status__in=[EncaixePaciente.Status.CHAMADO, EncaixePaciente.Status.ATENDIMENTO],

        ).order_by("-chamado_em").first()

        tipos = list(encaixe.tipos_atendimento.all())

        context = {

            "page_title": "Acompanhamento de Atendimento",

            "title_line_1": "Acompanhamento de",

            "title_line_2": "Atendimento",

            "subtitle": "Confira sua posição atual na fila",

            "paciente": encaixe.nome_completo,

            "senha": encaixe.senha,

            "cpf": encaixe.cpf,

            "sala_prevista": encaixe.sala or "Sala 1",

            "tipo_atendimento": tipos[0].get_tipo_display() if tipos else "Ambulatorial",

            "chamando_agora": chamando_agora.senha if chamando_agora else "---",

            "pacientes_a_frente": pacientes_a_frente,

            "mensagem": "Permaneça atento ao painel de chamadas e aguarde sua vez.",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

            "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),

        }

        return render(request, "mobile/acompanhamento_atendimento.html", context)

    return render(request, "mobile/acompanhamento_atendimento.html", get_acompanhamento_atendimento_context())


@xframe_options_sameorigin
def checagem_documentos_paciente_view(request):
    """Tela mobile do paciente para checar se está com os documentos
    necessários antes do exame auditivo (acessada pelo botão "Checar
    Documentos" da tela de Acompanhamento de Atendimento).

    A sessão do paciente manda: usamos resolver_encaixe_da_sessao (mesma
    função das demais telas do fluxo) e só recorremos ao `cpf`/`encaixe_id`
    da querystring como identificação de reserva quando não há nenhuma
    sessão de paciente válida. Antes, esses parâmetros da URL tinham
    prioridade sobre a sessão, o que permitia — em tese — que um paciente
    logado visse os documentos referentes a outro paciente, caso um link
    com o `cpf`/`encaixe_id` de outra pessoa fosse aberto no mesmo
    navegador.
    """
    encaixe = resolver_encaixe_da_sessao(request)

    if not encaixe:
        # Identificação de reserva: cobre o caso de o link ter sido aberto
        # sem nenhuma sessão de paciente ativa (ex.: sessão expirou entre a
        # tela de Acompanhamento e o clique em "Checar Documentos").
        encaixe_id_reserva = request.GET.get("encaixe_id", "").strip()
        cpf_reserva = request.GET.get("cpf", "").strip()
        if encaixe_id_reserva:
            encaixe = EncaixePaciente.objects.filter(pk=encaixe_id_reserva).first()
        elif cpf_reserva:
            encaixe = EncaixePaciente.objects.filter(
                cpf=cpf_reserva, data_atendimento=timezone.localdate(),
            ).order_by("-criado_em").first()

    voltar_url = reverse("acompanhamento-atendimento")

    if encaixe:
        tipos = list(encaixe.tipos_atendimento.all())
        exame_nome = tipos[0].get_tipo_display() if tipos else "Exame Auditivo"
    else:
        exame_nome = "Exame Auditivo"

    context = {
        "page_title": "Checar Documentos",
        "footer_indicators": [
            {"label": "LGPD", "detail": "Conforme", "icon": "lock"},
            {"label": "Conexão", "detail": "Segura", "icon": "shield"},
        ],
        "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),
        "voltar_url": voltar_url,
        "checklist_itens": [
            {
                "titulo": "Pedido Médico",
                "descricao": f"Pedido médico original com a solicitação do {exame_nome.lower()}.",
            },
            {
                "titulo": "Documento com Foto",
                "descricao": "RG, CNH ou outro documento oficial com foto.",
            },
            {
                "titulo": "Comprovante de Agendamento",
                "descricao": "Senha ou comprovante do seu check-in de hoje.",
            },
        ],
    }

    if encaixe:
        primeiro_nome = (encaixe.nome_completo or "").strip().split(" ")[0] or encaixe.nome_completo
        context.update({
            "paciente_nome": encaixe.nome_completo,
            "primeiro_nome": primeiro_nome,
            "exame_nome": exame_nome,
            "sala_prevista": encaixe.sala or "Sala 1",
            "senha": encaixe.senha,
            "cpf": encaixe.cpf,
        })
    else:
        context.update({
            "paciente_nome": "",
            "primeiro_nome": "Paciente",
            "exame_nome": exame_nome,
            "sala_prevista": "",
            "senha": "",
            "cpf": "",
        })

    return render(request, "mobile/checagem_documentos.html", context)


@xframe_options_sameorigin

def checkin_concluido_view(request):
    """Tela de confirmacao logo apos o check-in. Se a sessao resolve um
    encaixe de verdade, mostra a senha gerada; sem sessao valida, cai no
    contexto de exemplo (get_checkin_concluido_context)."""
    # Mesma resolução de sessão usada em todo o fluxo do paciente (ver
    # resolver_encaixe_da_sessao em core/services.py).
    encaixe = resolver_encaixe_da_sessao(request)

    if encaixe:

        context = {

            "page_title": "Check-in concluído",

            "title": "Check-in concluído",

            "subtitle": "Você já está na fila de atendimento",

            "paciente": encaixe.nome_completo,

            "senha": encaixe.senha,

            "mensagem": "Acompanhe sua posição na fila e aguarde sua chamada.",

            "texto_botao": "Acompanhar fila",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

            "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),

        }

        return render(request, "mobile/checkin_concluido.html", context)

    return render(request, "mobile/checkin_concluido.html", get_checkin_concluido_context())


@xframe_options_sameorigin

def checkin_assistido_view(request):

    """Tela estatica de orientacao pro paciente que precisa de ajuda
    presencial da recepcao pra fazer o check-in (sempre dados de exemplo,
    nao depende de sessao)."""

    return render(

        request,

        "mobile/checkin_assistido.html",

        get_checkin_assistido_context(),

    )


@xframe_options_sameorigin

def bloqueio_direcionamento_view(request):

    """Tela exibida quando o fluxo automatico do paciente e bloqueado e ele
    precisa ser direcionado manualmente pela recepcao (sempre dados de
    exemplo)."""

    return render(

        request,

        "mobile/bloqueio_direcionamento.html",

        get_bloqueio_direcionamento_context(),

    )


@xframe_options_sameorigin

def identificacao_paciente_view(request):

    """Primeira tela do fluxo mobile: recebe CPF (+ data de nascimento e
    nome da mae, quando exigidos por identidade_confere) e faz o check-in.

    Em caso de sucesso, a sessao e resetada por completo (session.flush())
    antes de gravar o novo paciente/encaixe -- isso e o que impede um
    dispositivo compartilhado (ex.: tablet da recepcao) de misturar dados
    de um paciente com o do check-in seguinte."""

    if request.method == "POST":

        form = IdentificacaoForm(request.POST)

        if form.is_valid():

            cpf = form.cleaned_data["cpf"]

            data_nasc = form.cleaned_data.get("data_nascimento")

            nome_mae = form.cleaned_data.get("nome_mae", "")



            paciente = Paciente.objects.filter(cpf=cpf, paciente_ativo=True).first()

            if not paciente:

                return redirect("agendamento_nao_encontrado")



            if not identidade_confere(paciente, data_nasc, nome_mae):

                return redirect("agendamento_nao_encontrado")



            encaixe = registrar_checkin(paciente, data_nasc, nome_mae)

            if not encaixe:

                return redirect("agendamento_nao_encontrado")



            request.session.flush()

            request.session["encaixe_id"] = encaixe.pk

            request.session["paciente_id"] = paciente.pk

            return redirect("checkin-concluido")



        context = {**get_identificacao_paciente_context(), "form": form}

        return render(request, "mobile/identificacao_paciente.html", context)

    context = {**get_identificacao_paciente_context(), "form": IdentificacaoForm()}

    return render(request, "mobile/identificacao_paciente.html", context)


def fluxo_paciente_view(request):

    """View unica que renderiza qualquer etapa do fluxo mobile do
    paciente dentro do mesmo template (mobile/fluxo_paciente.html),
    escolhida via ?step= (identificacao, checkin-assistido, bloqueio,
    agendamento-nao-encontrado, checkin-concluido, acompanhamento,
    paciente-chamado, perdeu-chamada).

    E uma tela de demonstracao/preview isolado -- serve pra ver qualquer
    etapa do fluxo sem precisar navegar pelo app de verdade. As telas
    "de producao" de cada etapa individual sao as views proprias (ex.:
    identificacao_paciente_view, checkin_assistido_view etc.); esta view
    nao substitui aquelas, so oferece um jeito rapido de visualizar tudo
    junto durante o desenvolvimento."""

    from datetime import date, datetime, timedelta



    dias_pt = ["SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA", "SEXTA-FEIRA", "SÁBADO", "DOMINGO"]

    meses_pt = ["", "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]



    step = request.GET.get("step", "identificacao")

    context = {

        "step": step,

        "page_title": "Fluxo do Paciente",

        "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),

        "cer_logo_url": _get_painel_chamada_asset_data_url("logo-cer.svg"),

    }



    if step == "identificacao":

        context.update({

            "page_title": "Identificação do Paciente",

            "title": "Bem-vindo",

            "subtitle": "Digite seus dados para iniciar o atendimento",

            "texto_botao_principal": "Realizar Check-in",

            "texto_botao_assistido": "Preciso de Ajuda",

            "validation_title": "Verificando seus dados",

            "validation_detail": "Conexão protegida",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

        })

        if request.method == "POST":

            form = IdentificacaoForm(request.POST)

            if form.is_valid():

                cpf = form.cleaned_data["cpf"]

                data_nasc = form.cleaned_data.get("data_nascimento")

                nome_mae = form.cleaned_data.get("nome_mae", "")



                if cpf == "00000000000":

                    return redirect(f"{reverse('fluxo-paciente')}?step=bloqueio")



                paciente = Paciente.objects.filter(cpf=cpf, paciente_ativo=True).first()

                if not paciente:

                    return redirect(f"{reverse('fluxo-paciente')}?step=agendamento-nao-encontrado")



                if not identidade_confere(paciente, data_nasc, nome_mae):

                    return redirect(f"{reverse('fluxo-paciente')}?step=agendamento-nao-encontrado")



                encaixe_ativo = EncaixePaciente.objects.filter(
                    cpf=cpf,
                    data_atendimento=timezone.localdate(),
                ).exclude(
                    status=EncaixePaciente.Status.CONCLUIDO,
                ).order_by("-criado_em").first()

                if encaixe_ativo:
                    step_map = {
                        EncaixePaciente.Status.AGUARDANDO: "acompanhamento",
                        EncaixePaciente.Status.CHAMADO: "paciente-chamado",
                        EncaixePaciente.Status.ATENDIMENTO: "paciente-chamado",
                        EncaixePaciente.Status.AUSENTE: "perdeu-chamada",
                    }
                    request.session["encaixe_id"] = encaixe_ativo.pk
                    request.session["paciente_id"] = paciente.pk
                    return redirect(
                        f"{reverse('fluxo-paciente')}?step={step_map.get(encaixe_ativo.status, 'acompanhamento')}"
                    )

                encaixe = registrar_checkin(paciente, data_nasc, nome_mae)

                if not encaixe:

                    return redirect(f"{reverse('fluxo-paciente')}?step=agendamento-nao-encontrado")



                request.session["encaixe_id"] = encaixe.pk

                request.session["paciente_id"] = paciente.pk

                return redirect(f"{reverse('fluxo-paciente')}?step=checkin-concluido")

            context["form"] = form

            return render(request, "mobile/fluxo_paciente.html", context)

        context["form"] = IdentificacaoForm()

        return render(request, "mobile/fluxo_paciente.html", context)



    if step == "checkin-assistido":

        context.update({

            "page_title": "Check-in Assistido",

            "title": "Siga para a Recepção",

            "message": "Nossa equipe no balcão principal ajudará com seu check-in. Por favor, tenha um documento com foto em mãos.",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

        })

        return render(request, "mobile/fluxo_paciente.html", context)



    if step == "bloqueio":

        context.update({

            "page_title": "Bloqueio e Direcionamento",

            "title_line_1": "Confirmação presencial",

            "title_line_2": "necessária",

            "subtitle": "Seus dados foram encontrados, mas seu atendimento precisa de confirmação presencial.",

            "next_step_label": "PRÓXIMO PASSO",

            "next_step_title": "Dirija-se à recepção",

            "next_step_description": "A equipe confirmará seus dados e orientará os próximos passos.",

            "location_label": "Local",

            "location": "Balcão da recepção",

            "info_message": "Seu atendimento continuará após a confirmação na recepção.",

            "status": "Confirmação na recepção",

            "review_label": "Revisar meus dados",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

        })

        return render(request, "mobile/fluxo_paciente.html", context)



    if step == "agendamento-nao-encontrado":

        return render(request, "mobile/fluxo_paciente.html", context)



    # Mesma resolução de sessão usada em todo o fluxo do paciente (ver
    # resolver_encaixe_da_sessao em core/services.py). Esse "encaixe" é
    # reaproveitado pelos passos finais deste wizard (checkin-concluido,
    # acompanhamento, paciente-chamado, perdeu-chamada).
    encaixe = resolver_encaixe_da_sessao(request)

    if step == "checkin-concluido" and encaixe:

        context.update({

            "page_title": "Check-in concluído",

            "title": "Check-in concluído",

            "subtitle": "Você já está na fila de atendimento",

            "paciente": encaixe.nome_completo,

            "senha": encaixe.senha,

            "mensagem": "Acompanhe sua posição na fila e aguarde sua chamada.",

            "texto_botao": "Acompanhar fila",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

        })

        return render(request, "mobile/fluxo_paciente.html", context)



    if step == "acompanhamento" and encaixe:

        pacientes_a_frente = EncaixePaciente.objects.filter(
            data_atendimento=encaixe.data_atendimento,
            status__in=[EncaixePaciente.Status.AGUARDANDO, EncaixePaciente.Status.VALIDACAO],
            posicao_fila__lt=encaixe.posicao_fila,
        ).count()

        chamando_agora = EncaixePaciente.objects.filter(

            data_atendimento=encaixe.data_atendimento,

            status__in=[EncaixePaciente.Status.CHAMADO, EncaixePaciente.Status.ATENDIMENTO],

        ).order_by("-chamado_em").first()

        tipos = list(encaixe.tipos_atendimento.all())

        context.update({

            "page_title": "Acompanhamento de Atendimento",

            "title_line_1": "Acompanhamento de",

            "title_line_2": "Atendimento",

            "subtitle": "Confira sua posição atual na fila",

            "paciente": encaixe.nome_completo,

            "senha": encaixe.senha,

            "cpf": encaixe.cpf,

            "sala_prevista": encaixe.sala or "Sala 1",

            "tipo_atendimento": tipos[0].get_tipo_display() if tipos else "Ambulatorial",

            "chamando_agora": chamando_agora.senha if chamando_agora else "---",

            "pacientes_a_frente": pacientes_a_frente,

            "mensagem": "Permaneça atento ao painel de chamadas e aguarde sua vez.",

            "fo_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

        })

        return render(request, "mobile/fluxo_paciente.html", context)



    if step == "paciente-chamado" and encaixe:

        tipos = list(encaixe.tipos_atendimento.all())

        context.update({

            "page_title": "Paciente Chamado",

            "title": "PACIENTE CHAMADO",

            "subtitle": "Dirija-se ao local indicado para atendimento",

            "senha": encaixe.senha,

            "paciente": encaixe.nome_completo,

            "sala": encaixe.sala or "Sala 10",

            "cpf": encaixe.cpf,

            "tipo_atendimento": tipos[0].get_tipo_display() if tipos else "Ambulatorial",

            "status": "Chamada atual",

            "mensagem": "Se precisar de ajuda, procure a recepção.",

            "footer_indicators": [

                {"label": "LGPD", "detail": "Conforme", "icon": "lock"},

                {"label": "Conexão", "detail": "Segura", "icon": "shield"},

            ],

        })

        return render(request, "mobile/fluxo_paciente.html", context)



    if step == "perdeu-chamada" and encaixe:

        context.update({

            "page_title": "Senha Perdida",

            "atendimento": {

                "senha": encaixe.senha,

                "setor": "Recepção Central",

                "horario_chamada": encaixe.chamado_em.strftime("%H:%M") if encaixe.chamado_em else "--:--",

            },

        })

        return render(request, "mobile/fluxo_paciente.html", context)



    if step in ("checkin-concluido", "acompanhamento", "paciente-chamado", "perdeu-chamada") and not encaixe:

        return redirect(f"{reverse('fluxo-paciente')}?step=identificacao")



    return redirect(f"{reverse('fluxo-paciente')}?step=identificacao")


def perdeu_chamada_view(request, **kwargs):
    """Renderiza a tela de aviso de senha perdida para o paciente."""
    # Mesma resolução de sessão usada em todo o fluxo do paciente (ver
    # resolver_encaixe_da_sessao em core/services.py).
    encaixe = resolver_encaixe_da_sessao(request)

    if encaixe:

        context = {

            "page_title": "Senha Perdida",

            "atendimento": {

                "senha": encaixe.senha,

                "setor": "Recepção Central",

                "horario_chamada": encaixe.criado_em.strftime("%H:%M") if encaixe.criado_em else "--:--",

            }

        }

        return render(request, "mobile/perdeu_chamada.html", context)

    return render(request, "mobile/perdeu_chamada.html", {

        "page_title": "Senha Perdida",

        "atendimento": {

            "senha": "---",

            "setor": "Recepção Central",

            "horario_chamada": "--:--",

        }

    })


@require_http_methods(["GET"])

def paciente_status_api_view(request):

    """Endpoint simples de consulta por CPF (usado por telas que fazem
    polling do proprio status fora do fluxo de sessao normal). Devolve o
    encaixe mais recente daquele CPF, independente do dia."""

    cpf = request.GET.get("cpf", "").strip()

    if not cpf:

        return JsonResponse({"erro": "CPF obrigat\u00f3rio"}, status=400)

    encaixe = EncaixePaciente.objects.filter(cpf=cpf).order_by("-criado_em").first()

    if not encaixe:

        return JsonResponse({"erro": "Paciente n\u00e3o encontrado"}, status=404)

    return JsonResponse({

        "status": encaixe.status,

        "senha": encaixe.senha,

        "sala": encaixe.sala,

        "nome": encaixe.nome_completo,

    })


@xframe_options_sameorigin

def painel_pacientes_view(request):

    """Lista isolada das telas mobile destinadas ao usuário final."""

    return render(

        request,

        "mobile/painel_pacientes.html",

        {"screens": list_patient_screens()},

    )


@xframe_options_sameorigin

def checagem_documentos_view(request):

    """Renderiza a tela de checagem de documentos"""

    encaixe_id = request.GET.get("encaixe_id") or request.session.get("encaixe_id")
    cpf = request.GET.get("cpf", "").strip()

    encaixe = None
    if encaixe_id:
        encaixe = EncaixePaciente.objects.filter(pk=encaixe_id).first()
    if not encaixe and cpf:
        encaixe = EncaixePaciente.objects.filter(cpf=cpf).order_by("-criado_em").first()

    context = {
        "page_title": "Checagem de Documentos",
        "title": "Checagem de Documentos",
        "inter_font_url": _get_painel_chamada_asset_data_url("fonts/Inter-Variable.ttf"),
        "footer_indicators": [
            {"label": "LGPD", "detail": "Conforme", "icon": "lock"},
            {"label": "Conexão", "detail": "Segura", "icon": "shield"},
        ],
    }

    if encaixe:
        tipos = list(encaixe.tipos_atendimento.all())
        context["paciente_nome"] = encaixe.nome_completo
        context["exame_nome"] = tipos[0].get_tipo_display() if tipos else "Exame"
        context["recepcao"] = "Recepção 2"
        context["cpf"] = encaixe.cpf
    else:
        context["paciente_nome"] = "Paciente"
        context["exame_nome"] = "Exame"
        context["recepcao"] = "Recepção"
        context["cpf"] = ""

    return render(request, "system/checagem_documentos.html", context)


@xframe_options_sameorigin

def visualizar_agendamento_view(request):

    """Renderiza a tela de visualizar agendamento"""

    context = {}

    return render(request, "system/visualizar_agendamento.html", context)


@xframe_options_sameorigin

def agendamento_nao_encontrado_view(request):

    """Tela de erro exibida quando a identificacao falha (CPF sem cadastro,
    identidade nao confere, ou paciente sem agendamento/checkin pra hoje)."""

    return render(request, 'mobile/agendamento_nao_encontrado.html')


def area_paciente_view(request):

    """Placeholder pós-login: substituir pela próxima tela do fluxo do paciente."""

    paciente_id = request.session.get("paciente_id")

    if not paciente_id:

        return redirect("login")



    context = {"page_title": "Área do Paciente"}

    return render(request, "mobile/area_paciente.html", context)
