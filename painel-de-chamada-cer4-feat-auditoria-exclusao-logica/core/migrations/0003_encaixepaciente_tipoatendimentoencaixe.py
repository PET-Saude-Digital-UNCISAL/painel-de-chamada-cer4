from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_paciente'),
    ]

    operations = [
        migrations.CreateModel(
            name='EncaixePaciente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome_completo', models.CharField(max_length=150)),
                ('cpf', models.CharField(max_length=14)),
                ('data_nascimento', models.DateField(blank=True, null=True)),
                ('nome_mae', models.CharField(blank=True, max_length=150)),
                ('justificativa', models.TextField(blank=True)),
                ('anexo', models.FileField(blank=True, null=True, upload_to='encaixes/%Y/%m/%d/')),
                ('senha', models.CharField(max_length=10)),
                ('posicao_fila', models.PositiveIntegerField()),
                ('data_atendimento', models.DateField(default=django.utils.timezone.localdate)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'encaixe',
                'verbose_name_plural': 'encaixes',
                'ordering': ('posicao_fila',),
            },
        ),
        migrations.CreateModel(
            name='TipoAtendimentoEncaixe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('consulta', 'Consulta'), ('terapia', 'Terapia'), ('exame_auditivo', 'Exame Auditivo')], max_length=20)),
                ('encaixe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tipos_atendimento', to='core.encaixepaciente')),
            ],
            options={
                'verbose_name': 'tipo de atendimento',
                'verbose_name_plural': 'tipos de atendimento',
            },
        ),
    ]
