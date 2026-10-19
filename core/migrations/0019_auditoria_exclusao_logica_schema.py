# Fase 2 / Tarefa 2 -- schema de auditoria e exclusao logica.
#
# Aplica AuditoriaMixin + ExclusaoLogicaMixin em Paciente, EncaixePaciente
# e Agendamento. So estrutura: nenhum dado e alterado aqui.
#
# - Todas as colunas novas entram anulaveis, o que no PostgreSQL nao
#   reescreve a tabela.
# - EncaixePaciente.atualizado_em entra anulavel de proposito: a 0020
#   preenche e aplica o NOT NULL final.
# - A constraint "excluido_em e excluido_por juntos" entra aqui, e e
#   segura: nenhuma linha existente tem excluido_em/excluido_por.
# - Os AlterField de criado_em/atualizado_em mudam so o verbose_name (o
#   Django nao emite SQL).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_adiciona_choices_tipo_atendimento_agendamento'),
    ]

    operations = [
        migrations.AddField(
            model_name='paciente',
            name='criado_por',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.usuariosistema', verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='paciente',
            name='atualizado_por',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.usuariosistema', verbose_name='atualizado por'),
        ),
        migrations.AddField(
            model_name='paciente',
            name='excluido_por',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.usuariosistema', verbose_name='excluido por'),
        ),
        migrations.AddField(
            model_name='paciente',
            name='excluido_em',
            field=models.DateTimeField(blank=True, db_index=True, editable=False, null=True, verbose_name='excluido em'),
        ),
        migrations.AddField(
            model_name='agendamento',
            name='criado_por',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.usuariosistema', verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='agendamento',
            name='atualizado_por',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.usuariosistema', verbose_name='atualizado por'),
        ),
        migrations.AddField(
            model_name='agendamento',
            name='excluido_por',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.usuariosistema', verbose_name='excluido por'),
        ),
        migrations.AddField(
            model_name='agendamento',
            name='excluido_em',
            field=models.DateTimeField(blank=True, db_index=True, editable=False, null=True, verbose_name='excluido em'),
        ),
        migrations.AddField(
            model_name='encaixepaciente',
            name='criado_por',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.usuariosistema', verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='encaixepaciente',
            name='atualizado_por',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.usuariosistema', verbose_name='atualizado por'),
        ),
        migrations.AddField(
            model_name='encaixepaciente',
            name='excluido_por',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.usuariosistema', verbose_name='excluido por'),
        ),
        migrations.AddField(
            model_name='encaixepaciente',
            name='excluido_em',
            field=models.DateTimeField(blank=True, db_index=True, editable=False, null=True, verbose_name='excluido em'),
        ),
        # EncaixePaciente nao tinha atualizado_em. Entra anulavel aqui; a 0020
        # preenche e a 0021 aplica o NOT NULL final.
        migrations.AddField(
            model_name='encaixepaciente',
            name='atualizado_em',
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name='atualizado em'),
        ),
        migrations.AlterField(
            model_name='paciente',
            name='criado_em',
            field=models.DateTimeField(auto_now_add=True, verbose_name='criado em'),
        ),
        migrations.AlterField(
            model_name='agendamento',
            name='criado_em',
            field=models.DateTimeField(auto_now_add=True, verbose_name='criado em'),
        ),
        migrations.AlterField(
            model_name='encaixepaciente',
            name='criado_em',
            field=models.DateTimeField(auto_now_add=True, verbose_name='criado em'),
        ),
        migrations.AlterField(
            model_name='paciente',
            name='atualizado_em',
            field=models.DateTimeField(auto_now=True, verbose_name='atualizado em'),
        ),
        migrations.AlterField(
            model_name='agendamento',
            name='atualizado_em',
            field=models.DateTimeField(auto_now=True, verbose_name='atualizado em'),
        ),
        migrations.AddConstraint(
            model_name='paciente',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('excluido_em__isnull', True), ('excluido_por__isnull', True)), models.Q(('excluido_em__isnull', False), ('excluido_por__isnull', False)), _connector='OR'), name='paciente_excluido_em_e_por_juntos'),
        ),
        migrations.AddConstraint(
            model_name='agendamento',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('excluido_em__isnull', True), ('excluido_por__isnull', True)), models.Q(('excluido_em__isnull', False), ('excluido_por__isnull', False)), _connector='OR'), name='agendamento_excluido_em_e_por_juntos'),
        ),
        migrations.AddConstraint(
            model_name='encaixepaciente',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('excluido_em__isnull', True), ('excluido_por__isnull', True)), models.Q(('excluido_em__isnull', False), ('excluido_por__isnull', False)), _connector='OR'), name='encaixepaciente_excluido_em_e_por_juntos'),
        ),
    ]
