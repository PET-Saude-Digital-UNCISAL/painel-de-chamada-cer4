from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class UsuarioSistema(models.Model):
    class NivelAcesso(models.TextChoices):
        RECEPCIONISTA = "recepcionista", "Recepcionista"
        COORDENACAO = "coordenacao", "Coordenação"
        SUPER_ADMIN = "super_admin", "Super Admin"

    nome_completo = models.CharField(max_length=150)
    email_institucional = models.EmailField(unique=True)
    cpf = models.CharField(max_length=14, unique=True)
    nivel_acesso = models.CharField(max_length=20, choices=NivelAcesso.choices)
    cargo = models.CharField(max_length=100, blank=True, default="")
    departamento = models.CharField(max_length=100, blank=True, default="")
    foto_perfil = models.ImageField(upload_to='perfis/', null=True, blank=True)
    usuario_ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nome_completo",)
        verbose_name = "usuário do sistema"
        verbose_name_plural = "usuários do sistema"

    @property
    def iniciais(self):
        partes = self.nome_completo.split()
        return "".join(parte[0] for parte in partes[:2]).upper()

    def __str__(self):
        return self.nome_completo


class Paciente(models.Model):
    """Conta do portal do paciente (telas de Login e Criar Conta).

    Independente de UsuarioSistema: aqui é o paciente que acessa o próprio
    histórico/agendamentos, não a equipe interna do CER.
    """

    nome_completo = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, unique=True)
    data_nascimento = models.DateField(null=True, blank=True)
    email = models.EmailField(blank=True)
    senha_hash = models.CharField(max_length=128)
    paciente_ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nome_completo",)
        verbose_name = "paciente"
        verbose_name_plural = "pacientes"

    def set_senha(self, senha_plana: str) -> None:
        self.senha_hash = make_password(senha_plana)

    def checar_senha(self, senha_plana: str) -> bool:
        return check_password(senha_plana, self.senha_hash)

    def __str__(self):
        return self.nome_completo


class EncaixePaciente(models.Model):
    """Registro de encaixe manual de paciente na fila do dia."""

    nome_completo = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14)
    data_nascimento = models.DateField(null=True, blank=True)
    nome_mae = models.CharField(max_length=150, blank=True)
    justificativa = models.TextField(blank=True)
    anexo = models.FileField(upload_to="encaixes/%Y/%m/%d/", null=True, blank=True)
    senha = models.CharField(max_length=10)
    posicao_fila = models.PositiveIntegerField()
    data_atendimento = models.DateField(default=timezone.localdate)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("posicao_fila",)
        verbose_name = "encaixe"
        verbose_name_plural = "encaixes"

    def __str__(self):
        return f"{self.senha} — {self.nome_completo}"


class TipoAtendimentoEncaixe(models.Model):
    """Tipos de atendimento vinculados a um encaixe (pode ser mais de um)."""

    CONSULTA = "consulta"
    TERAPIA = "terapia"
    EXAME_AUDITIVO = "exame_auditivo"
    TIPOS = [
        (CONSULTA, "Consulta"),
        (TERAPIA, "Terapia"),
        (EXAME_AUDITIVO, "Exame Auditivo"),
    ]

    encaixe = models.ForeignKey(
        EncaixePaciente, on_delete=models.CASCADE, related_name="tipos_atendimento"
    )
    tipo = models.CharField(max_length=20, choices=TIPOS)

    class Meta:
        verbose_name = "tipo de atendimento"
        verbose_name_plural = "tipos de atendimento"

    def __str__(self):
        return self.get_tipo_display()
