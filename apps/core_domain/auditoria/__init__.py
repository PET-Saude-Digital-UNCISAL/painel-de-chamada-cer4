"""Auditoria (quem criou/alterou/excluiu e quando) e exclusao logica.

Fundacao usada pelos models Paciente, EncaixePaciente e Agendamento:
- contexto.py: ator atual (UsuarioSistema) num ContextVar;
- middleware.py: define o ator a partir da sessao do staff;
- querysets.py: SoftDeleteQuerySet e os managers `objects`/`all_objects`;
- mixins.py: AuditoriaMixin e ExclusaoLogicaMixin.

Os mixins nao sao importados aqui porque dependem do registro de apps do
Django; importe direto de `apps.core_domain.auditoria.mixins`.
"""

from apps.core_domain.auditoria.contexto import (
    definir_ator,
    get_ator_atual_id,
    restaurar_ator,
    usando_ator,
)

__all__ = ["definir_ator", "get_ator_atual_id", "restaurar_ator", "usando_ator"]
