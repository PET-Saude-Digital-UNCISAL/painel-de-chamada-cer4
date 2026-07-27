from django.db import models


class PesquisaSatisfacao(models.Model):
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
    comentario = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "core"
        ordering = ("-criado_em",)
        verbose_name = "pesquisa de satisfação"
        verbose_name_plural = "pesquisas de satisfação"

    def __str__(self):
        return f"{self.paciente_nome or self.paciente_cpf} — {self.nota}★"
