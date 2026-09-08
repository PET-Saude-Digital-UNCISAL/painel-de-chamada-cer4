from django.db import models
from django.utils import timezone


class EncaixePaciente(models.Model):
    """Uma senha na fila de atendimento de um dia especifico.

    E o registro central de todo o fluxo de chamada: cada vez que um
    paciente faz check-in (a partir de um agendamento) ou e encaixado pela
    recepcao (sem agendamento previo), nasce um EncaixePaciente novo para
    aquele dia. O painel de chamada, o acompanhamento do paciente e a
    auditoria de percurso trabalham todos em cima desse modelo.

    Um mesmo paciente (mesmo CPF) pode ter mais de um EncaixePaciente no
    mesmo dia -- por exemplo, dois tipos de atendimento diferentes -- e por
    isso a senha so precisa ser unica dentro do dia (unique_together com
    data_atendimento), nao globalmente.
    """

    class Status(models.TextChoices):
        # Ordem esperada de transicao: VALIDACAO -> AGUARDANDO -> CHAMADO ->
        # ATENDIMENTO -> CONCLUIDO. AUSENTE acontece quando o paciente e
        # chamado e nao comparece.
        VALIDACAO = "validacao", "Validação"
        AGUARDANDO = "aguardando", "Aguardando"
        CHAMADO = "chamado", "Chamado"
        ATENDIMENTO = "atendimento", "Em Atendimento"
        AUSENTE = "ausente", "Ausente"
        CONCLUIDO = "concluido", "Concluído"

    class Origem(models.TextChoices):
        # De onde veio esta senha: CHECKIN quando o paciente ja tinha
        # agendamento e so confirmou presenca; ENCAIXE quando a recepcao
        # adicionou o paciente na fila sem agendamento previo.
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
    # Quantas vezes essa senha foi chamada no painel -- usado pra decidir
    # quando desistir de chamar e marcar como ausente.
    vezes_chamado = models.PositiveSmallIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    origem = models.CharField(max_length=10, choices=Origem.choices, default=Origem.ENCAIXE)

    class Meta:
        app_label = "core"
        ordering = ("posicao_fila",)
        verbose_name = "encaixe"
        verbose_name_plural = "encaixes"
        # A senha se repete de um dia pro outro (a fila reinicia todo dia),
        # entao a unicidade so faz sentido dentro do mesmo data_atendimento.
        unique_together = ("senha", "data_atendimento")

    def __str__(self):
        return f"{self.senha} — {self.nome_completo}"
