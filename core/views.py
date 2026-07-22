import csv
import json

from django.conf import settings
from django.db import IntegrityError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from core.dev_builders import build_fake_screen_list, build_mocked_screen_payload
from core.forms import CadastroPacienteForm, EncaixeForm, LoginPacienteForm, MeuPerfilForm, PacientePerfilForm, UsuarioSistemaForm
from core.models import Paciente, UsuarioSistema
from core.services import (
    get_acompanhamento_atendimento_context,
    get_auditoria_percurso_context,
    get_bloqueio_direcionamento_context,
    get_cadastro_context,
    get_checkin_assistido_context,
    get_checkin_concluido_context,
    get_dashboard_monitoramento_context,
    get_identificacao_paciente_context,
    get_login_context,
    get_painel_chamada_context,
    get_paciente_chamado_context,
    get_screen_context,
    list_patient_screens,
    registrar_encaixe,
)


def _usuario_logado(request):
    uid = request.session.get("staff_usuario_id")
    return UsuarioSistema.objects.filter(pk=uid).first() if uid else None


@xframe_options_sameorigin
def dashboard_monitoramento_view(request):
    """Renderiza o dashboard de monitoramento com dados fictícios."""
    context = get_dashboard_monitoramento_context()
    context["interno"] = request.GET.get("interno") == "1"
    context["usuario_logado"] = _usuario_logado(request)
    return render(request, "core/dashboard_monitoramento.html", context)


@xframe_options_sameorigin
def painel_chamada_view(request):
    return render(request, "core/painel_chamada.html", get_painel_chamada_context())


@xframe_options_sameorigin
def paciente_chamado_view(request):
    return render(request, "core/paciente_chamado.html", get_paciente_chamado_context())


@xframe_options_sameorigin
def acompanhamento_atendimento_view(request):
    return render(
        request,
        "core/acompanhamento_atendimento.html",
        get_acompanhamento_atendimento_context(),
    )


@xframe_options_sameorigin
def checkin_concluido_view(request):
    return render(
        request,
        "core/checkin_concluido.html",
        get_checkin_concluido_context(),
    )


@xframe_options_sameorigin
def checkin_assistido_view(request):
    return render(
        request,
        "core/checkin_assistido.html",
        get_checkin_assistido_context(),
    )


@xframe_options_sameorigin
def bloqueio_direcionamento_view(request):
    return render(
        request,
        "core/bloqueio_direcionamento.html",
        get_bloqueio_direcionamento_context(),
    )


@xframe_options_sameorigin
def identificacao_paciente_view(request):
    return render(
        request,
        "core/identificacao_paciente.html",
        get_identificacao_paciente_context(),
    )


@xframe_options_sameorigin
def configuracoes_view(request):
    """Manage access settings and persist institutional users."""
    usuario_id = request.session.get("staff_usuario_id")
    usuario_logado = UsuarioSistema.objects.filter(pk=usuario_id).first() if usuario_id else None
    is_admin = usuario_logado and usuario_logado.nivel_acesso == UsuarioSistema.NivelAcesso.SUPER_ADMIN
    tabela_vazia = not UsuarioSistema.objects.exists()

    form = UsuarioSistemaForm()
    edit_form = None
    edit_user = None
    if request.method == "POST":
        # Permite criar o primeiro usuário mesmo sem sessão de admin
        if not is_admin and not tabela_vazia:
            return redirect("sistema-interno")
        action = request.POST.get("action", "create")
        user_id = request.POST.get("usuario_id")

        if action == "create":
            form = UsuarioSistemaForm(request.POST)
            if form.is_valid():
                form.save()
                return _configuracoes_redirect(request, "criado")
        else:
            edit_user = get_object_or_404(UsuarioSistema, pk=user_id)
            if action == "update":
                edit_form = UsuarioSistemaForm(request.POST, instance=edit_user)
                if edit_form.is_valid():
                    edit_form.save()
                    return _configuracoes_redirect(request, "atualizado")
            elif action == "toggle":
                edit_user.usuario_ativo = not edit_user.usuario_ativo
                edit_user.save(update_fields=("usuario_ativo", "atualizado_em"))
                return _configuracoes_redirect(request, "status")
            elif action == "delete":
                edit_user.delete()
                return _configuracoes_redirect(request, "excluido")

    todos_usuarios = UsuarioSistema.objects.all()

    # Paginação: 10 usuários por página
    from django.core.paginator import Paginator
    paginator = Paginator(todos_usuarios, 10)
    pagina_atual = request.GET.get("pagina", 1)
    page_obj = paginator.get_page(pagina_atual)

    context = {
        "usuario_form": form,
        "edit_form": edit_form,
        "edit_user": edit_user,
        "usuarios": page_obj,
        "page_obj": page_obj,
        "is_admin": is_admin,
        "pode_criar": is_admin or tabela_vazia,
        "usuario_logado": usuario_logado,
        "usuarios_ativos": todos_usuarios.filter(usuario_ativo=True).count(),
        "abrir_gestao_usuarios": request.GET.get("modulo") == "usuarios" or request.method == "POST",
        "resultado": request.GET.get("resultado", ""),
        "interno": request.GET.get("interno") == "1",
        "configuracoes_action_url": (
            f"{reverse('configuracoes')}?interno=1"
            if request.GET.get("interno") == "1"
            else reverse("configuracoes")
        ),
    }
    return render(request, "core/configuracoes.html", context)


def _configuracoes_redirect(request, resultado):
    """Mantém formulários de configurações dentro do painel quando abertos nele."""
    if request.GET.get("interno") == "1":
        return redirect(
            f"{reverse('sistema-interno')}?tela=configuracoes&modulo=usuarios&resultado={resultado}"
        )
    return redirect(f"{reverse('configuracoes')}?modulo=usuarios&resultado={resultado}")


def perdeu_chamada_view(request, **kwargs):
    """Renderiza a tela de aviso de senha perdida para o paciente."""
    context = {
        "page_title": "Senha Perdida",
        "atendimento": {
            "senha": "A-104",
            "setor": "Recepção Central",
            "horario_chamada": "14:32"
        }
    }
    return render(request, "core/perdeu_chamada.html", context)


@xframe_options_sameorigin
def home_view(request):
    """Entrada do painel isolado, limitada aos dois fluxos do produto."""
    request.session.pop("staff_logged_in", None)
    return render(request, "core/home.html", {"title": "Painel de desenvolvimento"})


@xframe_options_sameorigin
def painel_pacientes_view(request):
    """Lista isolada das telas mobile destinadas ao usuário final."""
    return render(
        request,
        "core/painel_pacientes.html",
        {"screens": list_patient_screens()},
    )


def sistema_interno_view(request):
    """Shell único do sistema interno; a tela é escolhida pelo parâmetro ``tela``."""
    screens = {
        "monitoramento": {"label": "Monitoramento do fluxo", "path": f"{reverse('dashboard-monitoramento')}?interno=1"},
        "perfil": {"label": "Meu perfil", "path": f"{reverse('meu-perfil')}?interno=1"},
        "triagem": {"label": "Triagem", "path": None},
        "chamadas": {"label": "Chamadas", "path": None},
        "presenca": {"label": "Controle de presença", "path": None},
        "relatorios": {"label": "Relatórios de desempenho", "path": None},
        "qualidade": {"label": "Gestão da qualidade", "path": f"{reverse('gestao_qualidade')}?interno=1"},
        "auditoria": {"label": "Auditoria e segurança", "path": f"{reverse('screen-auditoria-percurso-seguranca')}?interno=1"},
        "configuracoes": {"label": "Configurações", "path": f"{reverse('configuracoes')}?interno=1"},
        "login": {"label": "Login", "path": f"{reverse('login')}?interno=1"},
        "cadastro": {"label": "Cadastro", "path": f"{reverse('cadastro')}?interno=1"},
    }
    def items(*keys):
        return [{"key": key, **screens[key]} for key in keys]

    navigation_groups = [
        {"role": "Colaboradores", "screens": items("monitoramento", "perfil", "triagem", "chamadas", "presenca")},
        {"role": "Gerência", "screens": items("relatorios", "qualidade", "auditoria")},
        {"role": "SuperAdmin", "screens": items("configuracoes")},
        {"role": "Acesso ao sistema", "screens": items("login", "cadastro")},
    ]
    active_key = request.GET.get("tela", "monitoramento")
    if active_key not in screens:
        active_key = "monitoramento"
    return render(request, "core/sistema_interno.html", {
        "navigation_groups": navigation_groups,
        "active_key": active_key,
        "active_screen": screens[active_key],
    })


@xframe_options_sameorigin
def sistema_interno_figma_view(request):
    """Shell do sistema interno com o Drawer aprovado no Figma."""
    if not request.session.get("staff_logged_in"):
        return redirect("login")
    screens = {
        "auditoria": {"label": "Atendimentos do Dia", "path": f"{reverse('screen-auditoria-percurso-seguranca')}?interno=1"},
        "monitoramento": {"label": "Dashboard", "path": f"{reverse('dashboard-monitoramento')}?interno=1"},
        "relatorios": {"label": "Relatorios de Desempenho", "path": f"{reverse('screen-relatorios-desempenho')}?interno=1"},
        "qualidade": {"label": "Gestao de Qualidade", "path": f"{reverse('gestao_qualidade')}?interno=1"},
        "configuracoes": {"label": "Configuracoes", "path": f"{reverse('configuracoes')}?interno=1"},
        "perfil": {"label": "Meu Perfil", "path": f"{reverse('meu-perfil')}?interno=1"},
        # Acesso institucional: intencionalmente fora do Drawer do Figma.
        "login": {"label": "Login", "path": f"{reverse('login')}?interno=1"},
        "cadastro": {"label": "Cadastro", "path": f"{reverse('cadastro')}?interno=1"},
    }
    active_key = request.GET.get("tela", "auditoria")
    if active_key not in screens:
        active_key = "auditoria"
    navigation_items = [
        {"key": key, **screens[key]}
        for key in ("auditoria", "monitoramento", "relatorios", "qualidade", "configuracoes", "perfil")
    ]
    return render(request, "core/sistema_interno.html", {
        "navigation_items": navigation_items,
        "active_key": active_key,
        "active_screen": screens[active_key],
    })

@xframe_options_sameorigin
def checagem_documentos_view(request):
    """Renderiza a tela de checagem de documentos"""
    context = {}
    return render(request, "telas/cris/checagem_documentos.html", context)


@xframe_options_sameorigin
def relatorios_desempenho_view(request):
    """Renderiza a tela de relatórios de desempenho"""
    context = {}
    return render(request, "telas/cris/relatorios_desempenho.html", context)


@xframe_options_sameorigin
def visualizar_agendamento_view(request):
    """Renderiza a tela de visualizar agendamento"""
    context = {}
    return render(request, "telas/cris/visualizar_agendamento.html", context)

def screen_view(request, screen_slug):
    """Thin view: only render context produced by the application service."""
    context = get_screen_context(screen_slug)
    if context is None:
        raise Http404("Tela não encontrada")
    return render(request, "core/screen.html", context)


@xframe_options_sameorigin
def auditoria_percurso_seguranca_view(request):
    """Thin view for the audit screen, keeping business data in services."""
    filtros = {
        "q": request.GET.get("q", ""),
        "data": request.GET.get("data", ""),
        "data_inicio": request.GET.get("data_inicio", ""),
        "data_fim": request.GET.get("data_fim", ""),
        "setor": request.GET.get("setor", ""),
        "status": request.GET.get("status", ""),
        "apenas_alertas": request.GET.get("apenas_alertas", ""),
    }

    context = get_auditoria_percurso_context(filtros)
    context["interno"] = request.GET.get("interno") == "1"
    context["usuario_logado"] = _usuario_logado(request)

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="auditoria_percurso_seguranca.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Ordem",
                "Ficha",
                "Paciente",
                "CPF",
                "Check-in",
                "Entrada Fila",
                "Chamada",
                "Encerramento",
                "Status",
                "Setor",
                "Data Referência",
                "Badges",
                "Log",
            ]
        )

        for paciente in context["pacientes"]:
            writer.writerow(
                [
                    paciente.get("ordem", ""),
                    paciente.get("ficha", ""),
                    paciente.get("nome", ""),
                    paciente.get("cpf", ""),
                    paciente.get("check_in", ""),
                    paciente.get("entrada_fila", ""),
                    paciente.get("chamada", ""),
                    paciente.get("encerramento", ""),
                    paciente.get("status", ""),
                    paciente.get("setor", ""),
                    paciente.get("data_referencia", ""),
                    " | ".join(paciente.get("badges", [])),
                    paciente.get("log", ""),
                ]
            )
        return response

    return render(request, "core/auditoria_percurso_seguranca.html", context)


def dev_mock_list_view(request):
    """Hidden route for isolated front-end work with generated fake cards."""
    if not settings.DEBUG:
        raise Http404("Not found")

    qty = int(request.GET.get("qty", "6"))
    context = {
        "title": "Preview de mocks",
        "cards": build_fake_screen_list(quantity=max(1, min(qty, 20))),
    }
    return render(request, "core/dev_preview.html", context)


def dev_mock_screen_view(request, screen_slug):
    """Hidden route to render one mocked screen without full DB setup."""
    if not settings.DEBUG:
        raise Http404("Not found")

    use_factory = request.GET.get("factory", "0") == "1"
    context = build_mocked_screen_payload(screen_slug=screen_slug, use_factory=use_factory)
    return render(request, "core/screen.html", context)


@xframe_options_sameorigin
def agendamento_nao_encontrado_view(request):
    return render(request, 'core/agendamento_nao_encontrado.html')


@xframe_options_sameorigin
def login_view(request):
    """Tela de Login — autentica paciente ou staff pelo CPF."""
    if request.session.get("staff_logged_in"):
        if request.GET.get("interno") != "1":
            return redirect("sistema-interno")
    if request.method == "POST":
        form = LoginPacienteForm(request.POST)
        if form.is_valid():
            cpf_digits = form.cleaned_data["cpf"]
            cpf_fmt = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"

            # Tenta encontrar staff primeiro
            usuario = UsuarioSistema.objects.filter(cpf=cpf_fmt, usuario_ativo=True).first()
            # Tenta encontrar paciente pelo CPF sem formatação
            paciente = Paciente.objects.filter(cpf=cpf_digits, paciente_ativo=True).first()

            request.session["staff_logged_in"] = True
            if usuario:
                request.session["staff_usuario_id"] = usuario.pk
            if paciente:
                request.session["paciente_id"] = paciente.pk
        return redirect("sistema-interno")
    context = {**get_login_context(), "form": LoginPacienteForm()}
    return render(request, "core/login.html", context)


@xframe_options_sameorigin
def cadastro_view(request):
    """Tela de Cadastro — persiste o paciente no banco com tratamento de erros."""
    if request.method == "POST":
        form = CadastroPacienteForm(request.POST)
        if form.is_valid():
            try:
                paciente = form.save()
                request.session["paciente_id"] = paciente.pk
                return redirect("login")
            except IntegrityError:
                form.add_error(None, "Erro ao salvar: CPF ou e-mail já cadastrado.")
        context = {**get_cadastro_context(), "form": form}
        return render(request, "core/cadastro.html", context)
    context = {**get_cadastro_context(), "form": CadastroPacienteForm()}
    return render(request, "core/cadastro.html", context)


def logout_view(request):
    request.session.flush()
    return redirect("login")


def area_paciente_view(request):
    """Placeholder pós-login: substituir pela próxima tela do fluxo do paciente."""
    paciente_id = request.session.get("paciente_id")
    if not paciente_id:
        return redirect("login")

    context = {"page_title": "Área do Paciente"}
    return render(request, "core/area_paciente.html", context)


@xframe_options_sameorigin
def gestao_qualidade_view(request):
    return render(request, 'core/gestao_qualidade.html', {
        "interno": request.GET.get("interno") == "1",
        "usuario_logado": _usuario_logado(request),
    })


@xframe_options_sameorigin
def pesquisa_satisfacao_view(request):
    return render(request, 'core/pesquisa_satisfacao.html')


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


@xframe_options_sameorigin
def meu_perfil_view(request):
    def _iniciais(nome):
        partes = (nome or "").split()
        return "".join(p[0] for p in partes[:2]).upper() or "?"

    def _ctx(interno, usuario, paciente, form, extra=None):
        instancia = paciente or usuario
        nome = instancia.nome_completo if instancia else "Sem vínculo"
        ctx = {
            "interno": interno,
            "usuario": usuario,
            "paciente": paciente,
            "form": form,
            "cpf_perfil": instancia.cpf if instancia else "",
            "nome_perfil": nome,
            "iniciais_perfil": _iniciais(nome),
            "papel_perfil": usuario.get_nivel_acesso_display() if usuario else "Paciente",
        }
        if extra:
            ctx.update(extra)
        return ctx

    interno = request.GET.get("interno") == "1"

    if not request.session.get("staff_logged_in"):
        return render(request, "core/meu_perfil.html", _ctx(
            interno, None, None, MeuPerfilForm(),
            {"erro": "Sessão expirada. Faça login novamente."}
        ))

    paciente_id = request.session.get("paciente_id")
    usuario_id = request.session.get("staff_usuario_id")
    paciente = Paciente.objects.filter(pk=paciente_id, paciente_ativo=True).first() if paciente_id else None
    usuario = UsuarioSistema.objects.filter(pk=usuario_id).first() if usuario_id else None

    FormClass = PacientePerfilForm if paciente else MeuPerfilForm
    instancia = paciente if paciente else usuario

    if request.method == "POST":
        if instancia is None:
            return render(request, "core/meu_perfil.html", _ctx(
                interno, None, None, FormClass(),
                {"erro": "Usuário não vinculado à sessão. Faça login novamente."}
            ))
        form = FormClass(request.POST, instance=instancia)
        if form.is_valid():
            try:
                form.save()
                return render(request, "core/meu_perfil.html", _ctx(
                    interno, usuario, paciente, form, {"sucesso": True}
                ))
            except IntegrityError:
                form.add_error(None, "Erro ao salvar: dado já em uso por outro cadastro.")
        return render(request, "core/meu_perfil.html", _ctx(interno, usuario, paciente, form))

    form = FormClass(instance=instancia) if instancia else FormClass()
    return render(request, "core/meu_perfil.html", _ctx(interno, usuario, paciente, form))
