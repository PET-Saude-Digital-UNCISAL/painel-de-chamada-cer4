import csv

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.dev_builders import build_fake_screen_list, build_mocked_screen_payload
from core.forms import UsuarioSistemaForm
from core.models import UsuarioSistema
from core.services import (
    get_auditoria_percurso_context,
    get_dashboard_monitoramento_context,
    get_screen_context,
    list_team_screens,
)


def dashboard_monitoramento_view(request):
    """Renderiza o dashboard de monitoramento com dados fictícios."""
    return render(request, "core/dashboard_monitoramento.html", get_dashboard_monitoramento_context())


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
                return redirect("/configuracoes/?modulo=usuarios&resultado=criado")
        else:
            edit_user = get_object_or_404(UsuarioSistema, pk=user_id)
            if action == "update":
                edit_form = UsuarioSistemaForm(request.POST, instance=edit_user)
                if edit_form.is_valid():
                    edit_form.save()
                    return redirect("/configuracoes/?modulo=usuarios&resultado=atualizado")
            elif action == "toggle":
                edit_user.usuario_ativo = not edit_user.usuario_ativo
                edit_user.save(update_fields=("usuario_ativo", "atualizado_em"))
                return redirect("/configuracoes/?modulo=usuarios&resultado=status")
            elif action == "delete":
                edit_user.delete()
                return redirect("/configuracoes/?modulo=usuarios&resultado=excluido")

    usuarios = UsuarioSistema.objects.all()
    context = {
        "usuario_form": form,
        "edit_form": edit_form,
        "edit_user": edit_user,
        "usuarios": usuarios,
        "usuarios_ativos": usuarios.filter(usuario_ativo=True).count(),
        "abrir_gestao_usuarios": request.GET.get("modulo") == "usuarios" or request.method == "POST",
        "resultado": request.GET.get("resultado", ""),
    }
    return render(request, "core/configuracoes.html", context)

def perdeu_chamada_view(request, **kwargs):
    """Renderiza a tela de aviso de senha perdida para o paciente."""
    # Criamos um dicionário simulando o que viria do builder/banco
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
    """Thin view: render dashboard with links for each isolated screen."""
    context = {
        "title": "Painel de desenvolvimento isolado",
        "screens": list_team_screens(),
    }
    return render(request, "core/home.html", context)


def screen_view(request, screen_slug):
    """Thin view: only render context produced by the application service."""
    context = get_screen_context(screen_slug)
    if context is None:
        raise Http404("Tela não encontrada")
    return render(request, "core/screen.html", context)


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
