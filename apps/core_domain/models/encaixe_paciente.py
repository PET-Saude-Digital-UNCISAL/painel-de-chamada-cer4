from django.db import models
from django.utils import timezone


class EncaixePaciente(models.Model):

    class Status(models.TextChoices):
        VALIDACAO = "validacao", "Validação"
        AGUARDANDO = "aguardando", "Aguardando"
        CHAMADO = "chamado", "Chamado"
        ATENDIMENTO = "atendimento", "Em Atendimento"
        AUSENTE = "ausente", "Ausente"
        CONCLUIDO = "concluido", "Concluído"

    class Origem(models.TextChoices):
        CHECKIN = "checkin", "Check-in"
        ENCAIXE = "encaixe", "Encaixe"

    nome_completo = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14)
    data_nascimento = models.DateField(null=True, blank=True)
    nome_mae = models.CharField(max_length=150, blank=True)
    justificativa = models.TextField(blank=True)
    anexo = models.FileField(upload_to="encaixes/%Y/%m/%d/", null=True, blank=True)
    senha = models.CharField(max_length=10)
    posicao_fila = models.PositiveIntegerField()
    data_atendimento = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VALIDACAO)
    sala = models.CharField(max_length=50, blank=True, default="")
    chamado_em = models.DateTimeField(null=True, blank=True)
    concluido_em = models.DateTimeField(null=True, blank=True)
    ausente_em = models.DateTimeField(null=True, blank=True)
    vezes_chamado = models.PositiveSmallIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    origem = models.CharField(max_length=10, choices=Origem.choices, default=Origem.ENCAIXE)

    class Meta:
        app_label = "core"
        ordering = ("posicao_fila",)
        verbose_name = "encaixe"
        verbose_name_plural = "encaixes"
        unique_together = ("senha", "data_atendimento")

    def __str__(self):
        return f"{self.senha} — {self.nome_completo}"
