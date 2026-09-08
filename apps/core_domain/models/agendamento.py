from django.db import models

from apps.core_domain.models.paciente import Paciente


class Agendamento(models.Model):
    """Um agendamento vindo do sistema de marcacao (importado via
    core/importer.py e core/integrador.py, ou lancado manualmente).

    E o compromisso original do paciente com uma data/hora; nao confundir
    com EncaixePaciente, que so existe a partir do momento em que o
    paciente de fato aparece e entra na fila do dia. Um Agendamento pode
    nunca virar um EncaixePaciente (se o paciente faltar) ou pode gerar um
    quando o check-in e feito.
    """

    class Status(models.TextChoices):
        AGENDADO = "agendado", "Agendado"
        CHECKIN_REALIZADO = "checkin_realizado", "Check-in Realizado"
        CANCELADO = "cancelado", "Cancelado"
        CONCLUIDO = "concluido", "Concluído"

    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="agendamentos"
    )
    data_agendamento = models.DateField()
    hora_agendamento = models.TimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AGENDADO
    )
    tipo_atendimento = models.CharField(max_length=20)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        ordering = ("paciente__nome_completo", "data_agendamento")
        verbose_name = "agendamento"
        verbose_name_plural = "agendamentos"

    def __str__(self):
        return f"{self.paciente.nome_completo} — {self.data_agendamento}"
