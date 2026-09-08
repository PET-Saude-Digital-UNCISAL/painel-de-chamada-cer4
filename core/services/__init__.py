"""Ponto de entrada do pacote core.services.

Mesma ideia do core/views/__init__.py: pacote sendo dividido por dominio
(Fase 3 do plano de refatoracao em docs/PLANO_REFATORACAO.md), um dominio
por vez. Por enquanto so autenticacao foi extraida; o resto ainda mora em
_legacy.py.

Reexporta tudo com o mesmo nome que existia em core/services.py antes da
divisao, entao qualquer `from core.services import nome_da_funcao` (usado
em core/views, apps/mobile/api/serializers.py, core/tests.py etc.)
continua funcionando sem mudar nada nesses arquivos. O "as X" redundante
em cada import e so para deixar explicito pro ruff/pyflakes que a
reexportacao e intencional.
"""

# SystemClock nao e definido aqui -- e so um import de core.clock que tanto
# _legacy.py quanto autenticacao.py usam internamente (SystemClock.now()).
# No core/services.py antigo (arquivo unico) esse import de nivel de modulo
# ja deixava SystemClock acessivel como core.services.SystemClock; precisamos
# reexportar explicitamente aqui para manter esse mesmo comportamento, pois
# core/test_clock_wrapper.py faz mock.patch("core.services.SystemClock").
from core.clock import SystemClock as SystemClock

from core.services._legacy import (
    PACIENTE_CHAMADO_ASSETS_DIR as PACIENTE_CHAMADO_ASSETS_DIR,
    PAINEL_CHAMADA_ASSETS_DIR as PAINEL_CHAMADA_ASSETS_DIR,
    SCREEN_DEFINITIONS as SCREEN_DEFINITIONS,
    STATUS_CLASS as STATUS_CLASS,
    STATUS_DISPLAY as STATUS_DISPLAY,
    ScreenDefinition as ScreenDefinition,
    _PainelChamadaDados as _PainelChamadaDados,
    _build_date_filter_modal_context as _build_date_filter_modal_context,
    _carregar_dados_painel as _carregar_dados_painel,
    _get_paciente_chamado_asset_data_url as _get_paciente_chamado_asset_data_url,
    _get_painel_chamada_asset_data_url as _get_painel_chamada_asset_data_url,
    _normalizar_nome as _normalizar_nome,
    _only_digits as _only_digits,
    _parse_iso_date as _parse_iso_date,
    _resolve_auditoria_date_range as _resolve_auditoria_date_range,
    filtrar_auditoria as filtrar_auditoria,
    get_acompanhamento_atendimento_context as get_acompanhamento_atendimento_context,
    get_auditoria_percurso_context as get_auditoria_percurso_context,
    get_bloqueio_direcionamento_context as get_bloqueio_direcionamento_context,
    get_checkin_assistido_context as get_checkin_assistido_context,
    get_checkin_concluido_context as get_checkin_concluido_context,
    get_dashboard_monitoramento_context as get_dashboard_monitoramento_context,
    get_identificacao_paciente_context as get_identificacao_paciente_context,
    get_paciente_chamado_context as get_paciente_chamado_context,
    get_painel_chamada_context as get_painel_chamada_context,
    get_screen_context as get_screen_context,
    identidade_confere as identidade_confere,
    list_patient_screens as list_patient_screens,
    list_team_screens as list_team_screens,
    registrar_checkin as registrar_checkin,
    registrar_encaixe as registrar_encaixe,
    resolver_encaixe_da_sessao as resolver_encaixe_da_sessao,
)

from core.services.autenticacao import (
    _DIAS_PT as _DIAS_PT,
    _MESES_PT as _MESES_PT,
    _cabecalho_recepcao_context as _cabecalho_recepcao_context,
    autenticar_paciente as autenticar_paciente,
    formatar_data_pt as formatar_data_pt,
    get_cadastro_context as get_cadastro_context,
    get_login_context as get_login_context,
)
