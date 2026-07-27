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
        "acompanhamento-atendimento/",
        views.acompanhamento_atendimento_view,
        name="acompanhamento-atendimento",
    ),
    path(
        "checkin-concluido/",
        views.checkin_concluido_view,
        name="checkin-concluido",
    ),
    path(
        "checkin-assistido/",
        views.checkin_assistido_view,
        name="checkin-assistido",
    ),
    path(
        "bloqueio-direcionamento/",
        views.bloqueio_direcionamento_view,
        name="bloqueio-direcionamento",
    ),
    path(
        "identificacao-paciente/",
        views.identificacao_paciente_view,
        name="identificacao-paciente",
    ),
    path(
        "telas/auditoria-percurso-seguranca/",
        views.auditoria_percurso_seguranca_view,
        name="screen-auditoria-percurso-seguranca",
    ),

    # Direct isolated routes for each team screen.
    path("telas/pacientes-listagem/", views.screen_view, {"screen_slug": "pacientes-listagem"}, name="screen-pacientes-listagem"),
    path("telas/cris/checagem_documentos.html", views.checagem_documentos_view, name="screen-checagem-documentos"),
    path("telas/cris/visualizar_agendamento.html", views.visualizar_agendamento_view, name="screen-visualizar-agendamento"),
    path("telas/dev2/", views.screen_view, {"screen_slug": "dev2"}, name="screen-dev2"),
    path("telas/dev3/", views.screen_view, {"screen_slug": "dev3"}, name="screen-dev3"),
    path("telas/dev4/", views.screen_view, {"screen_slug": "dev4"}, name="screen-dev4"),
    path("telas/dev6/", views.screen_view, {"screen_slug": "dev6"}, name="screen-dev6"),

    # Generic route if a new screen slug is created.
    path("telas/<slug:screen_slug>/", views.screen_view, name="screen-dynamic"),
    path('perdeu-chamada/', views.perdeu_chamada_view, name='perdeu_chamada'),
    path('api/paciente-status/', views.paciente_status_api_view, name='paciente-status-api'),
    path('api/dashboard/metrics/', views.dashboard_metrics_api, name='dashboard-metrics-api'),
    path('api/dashboard/metrics/export/', views.dashboard_metrics_export, name='dashboard-metrics-export'),
    path('api/dashboard/qualidade-metrics/', views.qualidade_metrics_api, name='qualidade-metrics-api'),
    path('agendamento-nao-encontrado/', views.agendamento_nao_encontrado_view, name='agendamento_nao_encontrado'),
    # Acesso institucional: login e cadastro pertencem ao sistema interno.
    path('login/', views.login_view, name='login'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('logout/', views.logout_view, name='logout'),
    path('area-paciente/', views.area_paciente_view, name='area-paciente'),
    path('gestao-qualidade/', views.gestao_qualidade_view, name='gestao_qualidade'),
    path('pesquisa-satisfacao/', views.pesquisa_satisfacao_view, name='pesquisa_satisfacao'),
    path('meu-perfil/', views.meu_perfil_view, name='meu-perfil'),
    path('encaixe/', views.encaixe_view, name='encaixe'),
    path('encaixe/<int:encaixe_id>/validar/', views.validar_encaixe_view, name='validar-encaixe'),
    path('encaixe/<int:encaixe_id>/iniciar-atendimento/', views.iniciar_atendimento_view, name='iniciar-atendimento'),
    path('encaixe/<int:encaixe_id>/concluir-atendimento/', views.concluir_atendimento_view, name='concluir-atendimento'),
    path('fluxo-paciente/', views.fluxo_paciente_view, name='fluxo-paciente'),
    path('api/integrador/sincronizar/', views.sincronizar_agendamentos_view, name='sincronizar-agendamentos'),
]
