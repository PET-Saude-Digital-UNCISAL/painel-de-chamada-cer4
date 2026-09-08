"""Ponto de entrada do pacote core.views.

Este pacote esta sendo dividido por dominio de tela (Fase 3 do plano de
refatoracao em docs/PLANO_REFATORACAO.md). Por enquanto so o dominio de
autenticacao foi extraido para o proprio modulo; o resto ainda mora em
_legacy.py e vai sendo migrado aos poucos, um dominio por vez.

Este __init__.py reexporta tudo com o MESMO nome que existia em
core/views.py antes da divisao, entao `core/urls.py` (que faz
`from core import views` e usa `views.nome_da_view`) continua funcionando
sem precisar mudar uma linha. O "as X" redundante em cada import e so
para deixar explicito pro ruff/pyflakes que a reexportacao e intencional
(sem isso ele acusa falso positivo de "import nao usado").
"""

from core.views._legacy import (
    _configuracoes_redirect as _configuracoes_redirect,
    _usuario_logado as _usuario_logado,
    acompanhamento_atendimento_view as acompanhamento_atendimento_view,
    agendamento_nao_encontrado_view as agendamento_nao_encontrado_view,
    area_paciente_view as area_paciente_view,
    auditoria_percurso_seguranca_view as auditoria_percurso_seguranca_view,
    bloqueio_direcionamento_view as bloqueio_direcionamento_view,
    checagem_documentos_paciente_view as checagem_documentos_paciente_view,
    checagem_documentos_view as checagem_documentos_view,
    checkin_assistido_view as checkin_assistido_view,
    checkin_concluido_view as checkin_concluido_view,
    concluir_atendimento_view as concluir_atendimento_view,
    configuracoes_view as configuracoes_view,
    dashboard_metrics_api as dashboard_metrics_api,
    dashboard_metrics_export as dashboard_metrics_export,
    dashboard_monitoramento_view as dashboard_monitoramento_view,
    dev_mock_list_view as dev_mock_list_view,
    dev_mock_screen_view as dev_mock_screen_view,
    encaixe_view as encaixe_view,
    fluxo_paciente_view as fluxo_paciente_view,
    gestao_qualidade_view as gestao_qualidade_view,
    health_check_view as health_check_view,
    home_view as home_view,
    identificacao_paciente_view as identificacao_paciente_view,
    iniciar_atendimento_view as iniciar_atendimento_view,
    meu_perfil_view as meu_perfil_view,
    paciente_chamado_view as paciente_chamado_view,
    paciente_status_api_view as paciente_status_api_view,
    painel_chamada_view as painel_chamada_view,
    painel_pacientes_view as painel_pacientes_view,
    perdeu_chamada_view as perdeu_chamada_view,
    pesquisa_satisfacao_view as pesquisa_satisfacao_view,
    qualidade_metrics_api as qualidade_metrics_api,
    salvar_permissoes_nivel_view as salvar_permissoes_nivel_view,
    screen_view as screen_view,
    sincronizar_agendamentos_view as sincronizar_agendamentos_view,
    sistema_interno_figma_view as sistema_interno_figma_view,
    validar_encaixe_view as validar_encaixe_view,
    visualizar_agendamento_view as visualizar_agendamento_view,
)

from core.views.autenticacao import (
    cadastro_view as cadastro_view,
    login_view as login_view,
    logout_view as logout_view,
)
