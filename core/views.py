import csv

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render

from core.dev_builders import build_fake_screen_list, build_mocked_screen_payload
from core.services import get_auditoria_percurso_context, get_screen_context, list_team_screens


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
