from django.urls import path

from core import views


urlpatterns = [
    path("", views.home_view, name="home"),
    path("pacientes/", views.painel_pacientes_view, name="painel-pacientes"),
    path("sistema-interno/", views.sistema_interno_figma_view, name="sistema-interno"),
    path("configuracoes/", views.configuracoes_view, name="configuracoes"),
    path(
        "dashboard-monitoramento/",
        views.dashboard_monitoramento_view,
        name="dashboard-monitoramento",
    ),
    path("painel-chamada/", views.painel_chamada_view, name="painel-chamada"),
    path("paciente-chamado/", views.paciente_chamado_view, name="paciente-chamado"),
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
    # Acesso institucional: login e cadastro pertencem ao sistema interno.
    path('login/', views.login_view, name='login'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('logout/', views.logout_view, name='logout'),
    path('area-paciente/', views.area_paciente_view, name='area-paciente'),
    path('gestao-qualidade/', views.gestao_qualidade_view, name='gestao_qualidade'),
    path('pesquisa-satisfacao/', views.pesquisa_satisfacao_view, name='pesquisa_satisfacao'),
    path('meu-perfil/', views.meu_perfil_view, name='meu-perfil'),
]
