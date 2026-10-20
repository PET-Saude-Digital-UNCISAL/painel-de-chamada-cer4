from django.db import migrations, models


class Migration(migrations.Migration):
    # Historico: essa migration originalmente usava SeparateDatabaseAndState
    # com database_operations=[] -- ou seja, so avisava o Django que os
    # campos existiam (mudava o "state"), sem gerar nenhum ALTER TABLE de
    # verdade. Resultado: em qualquer banco onde ela ja tivesse sido
    # aplicada, as colunas cargo/departamento nunca chegaram a existir de
    # fato, mas o django_migrations marcava a 0006 como aplicada.
    #
    # Foi corrigida em 27/07/2026 (commit 29ccd4c) para usar AddField normal,
    # que e o que esta abaixo hoje. Mas essa correcao so vale pra quem ainda
    # nao tinha rodado a 0006 -- editar uma migration depois que ela ja foi
    # aplicada em algum banco nao refaz retroativamente o que ja rodou. Quem
    # ja estava com o banco "adiantado" (0006 marcada como aplicada, colunas
    # ausentes) precisou da 0013 (ensure_cargo_departamento_columns), que
    # recria essas colunas via SQL direto com IF NOT EXISTS, independente do
    # que o historico de migrations diz.

    dependencies = [
        ('core', '0005_adiciona_status_sala_chamado_em'),
    ]

    operations = [
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
    ]
