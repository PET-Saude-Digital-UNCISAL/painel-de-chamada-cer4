"""Mixins abstratos de auditoria ("quem e quando") e exclusao logica.

Uso previsto (aplicado nos models pela tarefa de schema):

    class Paciente(AuditoriaMixin, ExclusaoLogicaMixin, models.Model):
        ...

A ordem importa: AuditoriaMixin primeiro, pra que o save() feito pela
exclusao logica tambem registre a ultima alteracao.

Os campos "por" apontam pra UsuarioSistema (o projeto nao usa o User do
Django) com on_delete=PROTECT: apagar um usuario que tem registros falha
com ProtectedError, e o caminho e desativar (usuario_ativo=False) pra
preservar o historico. Todos sao editable=False, entao ficam fora de
ModelForm, do form do admin e entram como read-only em ModelSerializer.
"""

from django.db import models
from django.utils import timezone

from apps.core_domain.auditoria.contexto import get_ator_atual_id
from apps.core_domain.auditoria.querysets import AllObjectsManager, SoftDeleteManager

CAMPOS_ALTERACAO = ("atualizado_em", "atualizado_por")
CAMPOS_EXCLUSAO = ("excluido_em", "excluido_por")


def _fk_usuario(verbose_name):
    # related_name="+" porque o mesmo mixin vai em varios models e o
    # UsuarioSistema nao precisa do acesso reverso (o PROTECT continua
    # valendo mesmo sem ele).
    return models.ForeignKey(
        "core.UsuarioSistema",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
        verbose_name=verbose_name,
    )


class AuditoriaMixin(models.Model):
    """criado_em/por e atualizado_em/por, preenchidos no save().

    O "por" vem do ator atual (ver auditoria/contexto.py). Sem ator --
    acao do paciente, rotina automatica sem `usando_ator` -- o campo fica
    nulo. criado_por nunca e sobrescrito depois de preenchido;
    atualizado_por sempre reflete a ultima alteracao, inclusive quando ela
    foi feita sem ator.

    update(), bulk_update() e update_or_create() na parte do update nao
    passam por aqui: quem usa precisa gravar os campos explicitamente.
    """

    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    criado_por = _fk_usuario("criado por")
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)
    atualizado_por = _fk_usuario("atualizado por")

    class Meta:
        abstract = True

    def save(self, **kwargs):
        ator_id = get_ator_atual_id()
        if self._state.adding and self.criado_por_id is None:
            self.criado_por_id = ator_id
        self.atualizado_por_id = ator_id

        # Sem isso, save(update_fields=[...]) -- muito usado no projeto --
        # nao atualizaria atualizado_em (auto_now so vale pros campos da
        # lista) nem atualizado_por. Lista vazia continua sendo "nao
        # salvar nada", como no Django.
        update_fields = kwargs.get("update_fields")
        if update_fields:
            kwargs["update_fields"] = {*update_fields, *CAMPOS_ALTERACAO}
        super().save(**kwargs)


class ExclusaoLogicaMixin(models.Model):
    """excluido_em/por e os managers `objects` (so ativos) e `all_objects`.

    `delete()` marca o registro como excluido em vez de apagar;
    `excluir_definitivamente()` apaga de verdade.
    """

    excluido_em = models.DateTimeField(
        "excluido em", null=True, blank=True, editable=False, db_index=True
    )
    excluido_por = _fk_usuario("excluido por")

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    @property
    def excluido(self) -> bool:
        return self.excluido_em is not None

    def delete(self, using=None, keep_parents=False):
        """Exclusao logica. Devolve o formato do delete() do Django.

        Nao propaga pra registros relacionados: cascata (ex.: paciente ->
        agendamentos) e regra de negocio, decidida em cada caso."""
        if self.excluido:
            return 0, {}
        self.excluido_em = timezone.now()
        self.excluido_por_id = get_ator_atual_id()
        self.save(using=using, update_fields=CAMPOS_EXCLUSAO)
        return 1, {self._meta.label: 1}

    delete.alters_data = True

    def restaurar(self, using=None) -> None:
        if not self.excluido:
            return
        self.excluido_em = None
        self.excluido_por = None
        self.save(using=using, update_fields=CAMPOS_EXCLUSAO)

    restaurar.alters_data = True

    def excluir_definitivamente(self, using=None, keep_parents=False):
        """DELETE de verdade no banco (ex.: eliminacao exigida pela LGPD)."""
        return super().delete(using=using, keep_parents=keep_parents)

    excluir_definitivamente.alters_data = True
