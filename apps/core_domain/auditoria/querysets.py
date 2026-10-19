"""QuerySet e managers da exclusao logica.

Contrato combinado entre as tarefas de auditoria:
- `objects`: so registros ativos (excluido_em nulo). E o manager padrao,
  entao views, forms, admin e related managers (`paciente.agendamentos`)
  deixam de enxergar os excluidos sem mudar nada no codigo chamador;
- `all_objects`: tudo, inclusive excluidos. Usar onde o excluido precisa
  contar -- geracao de senha/posicao da fila, busca por campo unique
  (CPF) antes de criar, restauracao.

`delete()` no queryset vira exclusao logica. A exclusao fisica so
acontece por `excluir_definitivamente()`, chamada de proposito.
"""

from django.db import models
from django.utils import timezone

from apps.core_domain.auditoria.contexto import get_ator_atual_id


def _campos_de_alteracao(model, agora, ator_id) -> dict:
    """Campos de "ultima alteracao" pra gravar junto num update() em massa,
    que nao passa pelo save() do AuditoriaMixin."""
    from apps.core_domain.auditoria.mixins import AuditoriaMixin

    if issubclass(model, AuditoriaMixin):
        return {"atualizado_em": agora, "atualizado_por_id": ator_id}
    return {}


class SoftDeleteQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(excluido_em__isnull=True)

    def excluidos(self):
        return self.filter(excluido_em__isnull=False)

    def delete(self):
        """Exclusao logica em massa. Registros ja excluidos sao ignorados,
        pra nao sobrescrever quando e por quem foram excluidos.

        Devolve o mesmo formato do delete() do Django:
        (total, {"app.Model": total})."""
        agora = timezone.now()
        ator_id = get_ator_atual_id()
        total = self.ativos().update(
            excluido_em=agora,
            excluido_por_id=ator_id,
            **_campos_de_alteracao(self.model, agora, ator_id),
        )
        return total, {self.model._meta.label: total}

    delete.alters_data = True
    delete.queryset_only = True

    def restaurar(self) -> int:
        agora = timezone.now()
        return self.excluidos().update(
            excluido_em=None,
            excluido_por_id=None,
            **_campos_de_alteracao(self.model, agora, get_ator_atual_id()),
        )

    restaurar.alters_data = True
    restaurar.queryset_only = True

    def excluir_definitivamente(self):
        """DELETE de verdade no banco (ex.: eliminacao exigida pela LGPD)."""
        return super().delete()

    excluir_definitivamente.alters_data = True
    excluir_definitivamente.queryset_only = True


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Manager que esconde os registros excluidos logicamente."""

    def get_queryset(self):
        return super().get_queryset().filter(excluido_em__isnull=True)


class AllObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Manager sem filtro: ativos e excluidos."""
