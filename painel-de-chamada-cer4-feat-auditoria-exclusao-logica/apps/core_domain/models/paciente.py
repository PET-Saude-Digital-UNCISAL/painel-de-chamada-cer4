from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.db import transaction

from apps.core_domain.auditoria.contexto import get_ator_atual_id

from apps.core_domain.auditoria.mixins import AuditoriaMixin, ExclusaoLogicaMixin


class Paciente(AuditoriaMixin, ExclusaoLogicaMixin, models.Model):
    """Cadastro de paciente, usado tanto no fluxo mobile (identificacao,
    check-in, acompanhamento) quanto como referencia para agendamentos e
    encaixes.

    O cadastro em si nao muda quando o paciente entra na fila -- quem
    representa "este paciente esta na fila hoje, nesta posicao, com este
    status" e o EncaixePaciente, criado a cada atendimento.
    """

    nome_completo = models.CharField(max_length=150)
    nome_mae = models.CharField(max_length=150, blank=True, default="")
    cpf = models.CharField(max_length=14, unique=True)
    data_nascimento = models.DateField(null=True, blank=True)
    email = models.EmailField(blank=True)
    # Hash da senha de acesso a area do paciente (portal), independente do
    # login institucional dos usuarios do sistema (UsuarioSistema).
    senha_hash = models.CharField(max_length=128)
    # Soft delete: paciente inativo continua no banco (por causa do
    # historico de agendamentos/encaixes), mas nao aparece mais como
    # identificavel nas telas do fluxo mobile.
    paciente_ativo = models.BooleanField(default=True)

    class Meta:
        app_label = "core"
        ordering = ("nome_completo",)
        verbose_name = "paciente"
        verbose_name_plural = "pacientes"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(excluido_em__isnull=True, excluido_por__isnull=True)
                    | models.Q(excluido_em__isnull=False, excluido_por__isnull=False)
                ),
                name="%(class)s_excluido_em_e_por_juntos",
            )
        ]

    def set_senha(self, senha_plana: str) -> None:
        self.senha_hash = make_password(senha_plana)

    def checar_senha(self, senha_plana: str) -> bool:
        return check_password(senha_plana, self.senha_hash)   
    
    @transaction.atomic
    def delete(self, using=None, keep_parents=False):
        if get_ator_atual_id() is None:
            raise ValueError("Excluir paciente exige um ator (usuário do sistema).")
        resultado = super().delete(using=using, keep_parents=keep_parents)
        if resultado[0]:
            campos = dict(
                excluido_em=self.excluido_em,
                excluido_por_id=self.excluido_por_id,
                atualizado_em=self.excluido_em,
                atualizado_por_id=self.excluido_por_id,
            )
            self.agendamentos.update(**campos)
            self.encaixes.update(**campos)
        return resultado

    @transaction.atomic
    def restaurar(self, using=None):
        from .agendamento import Agendamento
        from .encaixe_paciente import EncaixePaciente

        carimbo = self.excluido_em
        super().restaurar(using=using)
        if carimbo:
            Agendamento.all_objects.filter(paciente=self, excluido_em=carimbo).restaurar()
            EncaixePaciente.all_objects.filter(paciente=self, excluido_em=carimbo).restaurar()

    def __str__(self):
        return self.nome_completo
