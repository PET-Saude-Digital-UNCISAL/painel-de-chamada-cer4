from django.db import models


class TipoAtendimentoEncaixe(models.Model):
    CONSULTA = "consulta"
    TERAPIA = "terapia"
    EXAME_AUDITIVO = "exame_auditivo"
    TIPOS = [
        (CONSULTA, "Consulta"),
        (TERAPIA, "Terapia"),
        (EXAME_AUDITIVO, "Exame Auditivo"),
    ]

    encaixe = models.ForeignKey(
        "EncaixePaciente", on_delete=models.CASCADE, related_name="tipos_atendimento"
    )
    tipo = models.CharField(max_length=20, choices=TIPOS)

    class Meta:
        app_label = "core"
        verbose_name = "tipo de atendimento"
        verbose_name_plural = "tipos de atendimento"

    def __str__(self):
        return self.get_tipo_display()
