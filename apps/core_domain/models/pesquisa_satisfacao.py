from django.db import models


class PesquisaSatisfacao(models.Model):
    """Resposta da pesquisa de satisfacao preenchida pelo paciente depois
    do atendimento.

    Guarda nome/CPF do paciente separado do FK pro encaixe de proposito:
    a resposta tem que sobreviver mesmo se o EncaixePaciente correspondente
    for removido (por isso on_delete=SET_NULL), ja que o dado da pesquisa
    em si continua valioso pra gestao de qualidade independente do
    registro de fila que a originou.
    """

    encaixe = models.ForeignKey(
        "core.EncaixePaciente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pesquisas_satisfacao",
    )
    paciente_nome = models.CharField(max_length=150, blank=True)
    paciente_cpf = models.CharField(max_length=14, db_index=True)
    nota = models.PositiveSmallIntegerField()
    # Notas por atributo (1 a 5). Nulas em registros antigos, coletados antes
    # da pesquisa passar a perguntar por categoria — `nota` acima continua
    # sendo a nota geral (média das categorias quando presentes).
    nota_atendimento = models.PositiveSmallIntegerField(null=True, blank=True)
    nota_espera = models.PositiveSmallIntegerField(null=True, blank=True)
    nota_instalacao = models.PositiveSmallIntegerField(null=True, blank=True)
    nota_profissional = models.PositiveSmallIntegerField(null=True, blank=True)
    nota_clareza = models.PositiveSmallIntegerField(null=True, blank=True)
    comentario = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "core"
        ordering = ("-criado_em",)
        verbose_name = "pesquisa de satisfação"
        verbose_name_plural = "pesquisas de satisfação"

    def __str__(self):
        return f"{self.paciente_nome or self.paciente_cpf} — {self.nota}★"
