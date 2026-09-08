from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class Paciente(models.Model):
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
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        ordering = ("nome_completo",)
        verbose_name = "paciente"
        verbose_name_plural = "pacientes"

    def set_senha(self, senha_plana: str) -> None:
        self.senha_hash = make_password(senha_plana)

    def checar_senha(self, senha_plana: str) -> bool:
        return check_password(senha_plana, self.senha_hash)

    def __str__(self):
        return self.nome_completo
