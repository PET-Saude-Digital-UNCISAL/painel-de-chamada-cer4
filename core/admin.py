# Cadastro no Django Admin -- uso interno/tecnico (nao e a interface
# que a recepcao usa no dia a dia, essa fica nas telas do sistema
# interno). Util pra inspecionar/corrigir dados pontualmente.
from django.contrib import admin

from core.models import EncaixePaciente, Paciente, TipoAtendimentoEncaixe, UsuarioSistema


class TipoAtendimentoInline(admin.TabularInline):
    model = TipoAtendimentoEncaixe
    extra = 0


@admin.register(EncaixePaciente)
class EncaixePacienteAdmin(admin.ModelAdmin):
    list_display = ("senha", "nome_completo", "cpf", "data_atendimento", "posicao_fila", "criado_em")
    list_filter = ("data_atendimento",)
    search_fields = ("nome_completo", "cpf", "senha")
    inlines = (TipoAtendimentoInline,)


@admin.register(UsuarioSistema)
class UsuarioSistemaAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "email_institucional", "nivel_acesso", "usuario_ativo")
    list_filter = ("nivel_acesso", "usuario_ativo")
    search_fields = ("nome_completo", "email_institucional", "cpf")


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "cpf", "paciente_ativo", "criado_em")
    search_fields = ("nome_completo", "cpf")
