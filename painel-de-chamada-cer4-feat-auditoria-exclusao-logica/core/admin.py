# Cadastro no Django Admin -- uso interno/tecnico (nao e a interface
# que a recepcao usa no dia a dia, essa fica nas telas do sistema
# interno). Util pra inspecionar/corrigir dados pontualmente.
#
# Regras do admin para os models com auditoria/exclusao logica
# (Paciente, EncaixePaciente, Agendamento):
# - campos de auditoria e de exclusao sao somente leitura;
# - a listagem mostra so ativos por padrao; o filtro "Situacao" permite
#   ver excluidos ou todos;
# - nao ha exclusao (nem fisica nem logica) pelo admin: o admin nao tem
#   ator (staff_usuario_id e da sessao do sistema interno, nao do login
#   do admin), e a exclusao logica de Paciente exige ator. A unica acao
#   em massa e "Restaurar";
# - edicoes feitas pelo admin gravam atualizado_por vazio (sem ator).
from django.contrib import admin, messages

from core.models import (
    Agendamento,
    EncaixePaciente,
    Paciente,
    TipoAtendimentoEncaixe,
    UsuarioSistema,
)

CAMPOS_AUDITORIA = (
    "criado_em",
    "criado_por",
    "atualizado_em",
    "atualizado_por",
    "excluido_em",
    "excluido_por",
)


class SituacaoFilter(admin.SimpleListFilter):
    """Ativos (padrao), excluidos ou todos."""

    title = "situação"
    parameter_name = "situacao"

    def lookups(self, request, model_admin):
        return (("excluidos", "Excluídos"), ("todos", "Todos"))

    def choices(self, changelist):
        for valor, titulo in (
            (None, "Ativos"),
            ("excluidos", "Excluídos"),
            ("todos", "Todos"),
        ):
            if valor is None:
                url = changelist.get_query_string(remove=[self.parameter_name])
            else:
                url = changelist.get_query_string({self.parameter_name: valor})
            yield {
                "selected": self.value() == valor,
                "query_string": url,
                "display": titulo,
            }

    def queryset(self, request, queryset):
        valor = self.value()
        if valor == "todos":
            return queryset
        if valor == "excluidos":
            return queryset.filter(excluido_em__isnull=False)
        return queryset.filter(excluido_em__isnull=True)


class AuditoriaAdminMixin:
    """Comportamento comum dos admins de models com auditoria."""

    readonly_fields = CAMPOS_AUDITORIA
    actions = ("restaurar_selecionados",)

    def get_queryset(self, request):
        # `objects` esconde excluidos; o admin precisa enxergar todos pra
        # listar excluidos e abrir/restaurar um registro excluido. Quem
        # filtra ativos/excluidos na listagem e o SituacaoFilter.
        qs = self.model.all_objects.get_queryset()
        ordering = self.get_ordering(request)
        return qs.order_by(*ordering) if ordering else qs

    def has_delete_permission(self, request, obj=None):
        return False

    def delete_model(self, request, obj):
        raise PermissionError("Exclusão pelo admin não é permitida.")

    def delete_queryset(self, request, queryset):
        raise PermissionError("Exclusão pelo admin não é permitida.")

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    @admin.action(description="Restaurar registros excluídos selecionados")
    def restaurar_selecionados(self, request, queryset):
        restaurados = 0
        for obj in queryset.filter(excluido_em__isnull=False):
            # Nao restaura filho cujo paciente continua excluido: ficaria
            # um agendamento/encaixe ativo de um paciente invisivel.
            paciente = getattr(obj, "paciente", None)
            if (
                not isinstance(obj, Paciente)
                and paciente is not None
                and paciente.excluido
            ):
                self.message_user(
                    request,
                    f"{obj} não restaurado: o paciente está excluído. "
                    "Restaure o paciente primeiro.",
                    messages.WARNING,
                )
                continue
            obj.restaurar()
            restaurados += 1
        self.message_user(
            request, f"{restaurados} registro(s) restaurado(s).", messages.SUCCESS
        )


class TipoAtendimentoInline(admin.TabularInline):
    model = TipoAtendimentoEncaixe
    extra = 0


@admin.register(EncaixePaciente)
class EncaixePacienteAdmin(AuditoriaAdminMixin, admin.ModelAdmin):
    list_display = (
        "senha",
        "nome_completo",
        "cpf",
        "data_atendimento",
        "posicao_fila",
        "criado_em",
        "excluido_em",
    )
    list_filter = (SituacaoFilter, "data_atendimento")
    search_fields = ("nome_completo", "cpf", "senha")
    inlines = (TipoAtendimentoInline,)


@admin.register(Agendamento)
class AgendamentoAdmin(AuditoriaAdminMixin, admin.ModelAdmin):
    list_display = (
        "paciente",
        "data_agendamento",
        "hora_agendamento",
        "status",
        "excluido_em",
    )
    list_filter = (SituacaoFilter, "status", "data_agendamento")
    search_fields = ("paciente__nome_completo", "paciente__cpf")
    list_select_related = ("paciente",)


@admin.register(Paciente)
class PacienteAdmin(AuditoriaAdminMixin, admin.ModelAdmin):
    list_display = ("nome_completo", "cpf", "paciente_ativo", "criado_em", "excluido_em")
    list_filter = (SituacaoFilter, "paciente_ativo")
    search_fields = ("nome_completo", "cpf")


@admin.register(UsuarioSistema)
class UsuarioSistemaAdmin(admin.ModelAdmin):
    # Sem exclusao fisica: o usuario referenciado como autor em registros
    # nao pode ser apagado (PROTECT). O caminho e desativar
    # (usuario_ativo=False).
    list_display = ("nome_completo", "email_institucional", "nivel_acesso", "usuario_ativo")
    list_filter = ("nivel_acesso", "usuario_ativo")
    search_fields = ("nome_completo", "email_institucional", "cpf")

    def has_delete_permission(self, request, obj=None):
        return False
