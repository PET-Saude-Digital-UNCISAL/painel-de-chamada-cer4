from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_adiciona_status_sala_chamado_em'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='usuariosistema',
                    name='cargo',
                    field=models.CharField(default='', max_length=100),
                ),
                migrations.AddField(
                    model_name='usuariosistema',
                    name='departamento',
                    field=models.CharField(default='', max_length=100),
                ),
            ],
            database_operations=[],
        ),
    ]
