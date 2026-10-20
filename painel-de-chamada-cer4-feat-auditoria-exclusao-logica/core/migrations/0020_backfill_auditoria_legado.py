# Fase 2 / Tarefa 2 -- backfill dos registros anteriores a auditoria.
#
# * EncaixePaciente.atualizado_em (unica coluna nova com valor a preencher;
#   Paciente e Agendamento ja tinham a coluna) recebe criado_em.
# * Depois, a coluna passa a NOT NULL, como no AuditoriaMixin.
# * Registros antigos: criado_por/atualizado_por ficam NULOS. Decisao
#   vigente ("deixar nulos" no plano); se a equipe optar por um
#   UsuarioSistema "legado", e so acrescentar a criacao dele e o UPDATE
#   dos "por" nesta funcao.
#
# O reverso e um no-op: a 0019 reversa remove a coluna.

from django.db import migrations, models
from django.db.models import F


def preencher_atualizado_em(apps, schema_editor):
    EncaixePaciente = apps.get_model("core", "EncaixePaciente")
    EncaixePaciente.objects.filter(atualizado_em__isnull=True).update(
        atualizado_em=F("criado_em")
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_auditoria_exclusao_logica_schema'),
    ]

    operations = [
        migrations.RunPython(preencher_atualizado_em, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='encaixepaciente',
            name='atualizado_em',
            field=models.DateTimeField(auto_now=True, verbose_name='atualizado em'),
        ),
    ]
