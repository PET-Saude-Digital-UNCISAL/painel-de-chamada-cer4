from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_nivelacessopermissao'),
    ]

    operations = [
        migrations.AddField(
            model_name='pesquisasatisfacao',
            name='nota_atendimento',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pesquisasatisfacao',
            name='nota_espera',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pesquisasatisfacao',
            name='nota_instalacao',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pesquisasatisfacao',
            name='nota_profissional',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pesquisasatisfacao',
            name='nota_clareza',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
