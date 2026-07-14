import csv

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from core.dev_builders import build_fake_screen_list, build_mocked_screen_payload
from core.forms import CadastroPacienteForm, LoginPacienteForm, UsuarioSistemaForm
from core.models import UsuarioSistema
from core.services import (
    autenticar_paciente,
    get_auditoria_percurso_context,
    get_cadastro_context,
    get_dashboard_monitoramento_context,
    get_login_context,
    get_screen_context,
)


@xframe_options_sameorigin
def dashboard_monitoramento_view(request):
    """Renderiza o dashboard de monitoramento com dados fictícios."""
    context = get_dashboard_monitoramento_context()
    context["interno"] = request.GET.get("interno") == "1"
    return render(request, "core/dashboard_monitoramento.html", context)


@xframe_options_sameorigin
def configuracoes_view(request):
    """Manage access settings and persist institutional users."""
    form = UsuarioSistemaForm()
    edit_form = None
    edit_user = None
    if request.method == "POST":
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

    usuarios = UsuarioSistema.objects.all()
    context = {
        "usuario_form": form,
        "edit_form": edit_form,
        "edit_user": edit_user,
        "usuarios": usuarios,
        "usuarios_ativos": usuarios.filter(usuario_ativo=True).count(),
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


def home_view(request):
    """Entrada do painel isolado, limitada aos dois fluxos do produto."""
    return render(request, "core/home.html", {"title": "Painel de desenvolvimento"})


def painel_pacientes_view(request):
    """Lista isolada das telas mobile destinadas ao usuário final."""
    screens = [
        {
            "title": "Tela de Pesquisa de satisfação",
            "owner": "Monaliza",
            "path": reverse("pesquisa_satisfacao"),
        },
        {
            "title": "Tela de agendamento não encontrado",
            "owner": "Monaliza",
            "path": reverse("agendamento_nao_encontrado"),
        },
        {
            "title": "Tela de Perdeu a chamada",
            "owner": "Monaliza",
            "path": reverse("perdeu_chamada"),
        },
    ]
    return render(request, "core/painel_pacientes.html", {"screens": screens})


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


def sistema_interno_figma_view(request):
    """Shell do sistema interno com o Drawer aprovado no Figma."""
    if not request.session.get("staff_logged_in"):
        return redirect("login")
    screens = {
        "monitoramento": {"label": "Dashboard", "path": f"{reverse('dashboard-monitoramento')}?interno=1"},
        "relatorios": {"label": "Relatorios de Desempenho", "path": None},
        "auditoria": {"label": "Auditoria de Percurso", "path": f"{reverse('screen-auditoria-percurso-seguranca')}?interno=1"},
        "qualidade": {"label": "Gestao de Qualidade", "path": f"{reverse('gestao_qualidade')}?interno=1"},
        "configuracoes": {"label": "Configuracoes", "path": f"{reverse('configuracoes')}?interno=1"},
        "perfil": {"label": "Meu Perfil", "path": f"{reverse('meu-perfil')}?interno=1"},
        # Acesso institucional: intencionalmente fora do Drawer do Figma.
        "login": {"label": "Login", "path": f"{reverse('login')}?interno=1"},
        "cadastro": {"label": "Cadastro", "path": f"{reverse('cadastro')}?interno=1"},
    }
    active_key = request.GET.get("tela", "monitoramento")
    if active_key not in screens:
        active_key = "monitoramento"
    navigation_items = [
        {"key": key, **screens[key]}
        for key in ("monitoramento", "relatorios", "auditoria", "qualidade", "configuracoes", "perfil")
    ]
    return render(request, "core/sistema_interno.html", {
        "navigation_items": navigation_items,
        "active_key": active_key,
        "active_screen": screens[active_key],
    })

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


def agendamento_nao_encontrado_view(request):
    return render(request, 'core/agendamento_nao_encontrado.html')


@xframe_options_sameorigin
def login_view(request):
    """Tela de Login — qualquer submissão concede acesso ao sistema (protótipo)."""
    if request.session.get("staff_logged_in"):
        return redirect("sistema-interno")
    if request.method == "POST":
        request.session["staff_logged_in"] = True
        return redirect("sistema-interno")
    context = {**get_login_context(), "form": LoginPacienteForm()}
    return render(request, "core/login.html", context)


@xframe_options_sameorigin
def cadastro_view(request):
    """Tela de Cadastro — qualquer submissão redireciona ao login (protótipo)."""
    if request.method == "POST":
        request.session["staff_logged_in"] = True
        return redirect("sistema-interno")
    context = {**get_cadastro_context(), "form": CadastroPacienteForm()}
    return render(request, "core/cadastro.html", context)


def logout_view(request):
    request.session.pop("staff_logged_in", None)
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
    return render(request, 'core/gestao_qualidade.html', {"interno": request.GET.get("interno") == "1"})


def pesquisa_satisfacao_view(request):
    return render(request, 'core/pesquisa_satisfacao.html')


@xframe_options_sameorigin
def meu_perfil_view(request):
    return render(request, "core/meu_perfil.html", {"interno": request.GET.get("interno") == "1"})
