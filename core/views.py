from django.conf import settings
from django.http import Http404, HttpResponse  # <-- Adicionado HttpResponse aqui
from django.shortcuts import render

from core.dev_builders import build_fake_screen_list, build_mocked_screen_payload
from core.services import get_screen_context, list_team_screens

def perdeu_chamada_view(request):
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
def gestao_qualidade_view(request):
    return render(request, 'core/gestao_qualidade.html')
def pesquisa_satisfacao_view(request):
    return render(request, 'core/pesquisa_satisfacao.html')