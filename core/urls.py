from django.urls import path

from core import views


urlpatterns = [
    path("", views.home_view, name="home"),
    path("configuracoes/", views.configuracoes_view, name="configuracoes"),
    path(
        "dashboard-monitoramento/",
        views.dashboard_monitoramento_view,
        name="dashboard-monitoramento",
    ),
    path(
        "telas/auditoria-percurso-seguranca/",
        views.auditoria_percurso_seguranca_view,
        name="screen-auditoria-percurso-seguranca",
    ),

    # Direct isolated routes for each team screen.
    path("telas/pacientes-listagem/", views.screen_view, {"screen_slug": "pacientes-listagem"}, name="screen-pacientes-listagem"),
    path("telas/dev2/", views.screen_view, {"screen_slug": "dev2"}, name="screen-dev2"),
    path("telas/dev3/", views.screen_view, {"screen_slug": "dev3"}, name="screen-dev3"),
    path("telas/dev4/", views.screen_view, {"screen_slug": "dev4"}, name="screen-dev4"),
    path("telas/dev5/", views.screen_view, {"screen_slug": "dev5"}, name="screen-dev5"),
    path("telas/dev6/", views.screen_view, {"screen_slug": "dev6"}, name="screen-dev6"),

    # Generic route if a new screen slug is created.
    path("telas/<slug:screen_slug>/", views.screen_view, name="screen-dynamic"),
    path('perdeu-chamada/', views.perdeu_chamada_view, name='perdeu_chamada'),
    path('agendamento-nao-encontrado/', views.agendamento_nao_encontrado_view, name='agendamento_nao_encontrado'),
]
