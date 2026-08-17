from django.db import migrations, models


PERFIS_PADRAO = {
    "recepcionista": ["checkin"],
    "coordenacao": ["checkin", "prontuario", "usuarios", "auditoria"],
    "super_admin": ["checkin", "prontuario", "usuarios", "auditoria", "deletar"],
}

TODAS_PERMISSOES = ["checkin", "prontuario", "usuarios", "auditoria", "deletar"]


def seed_permissoes(apps, schema_editor):
    NivelAcessoPermissao = apps.get_model("core", "NivelAcessoPermissao")
    objetos = []
    for nivel, ativas in PERFIS_PADRAO.items():
        for permissao in TODAS_PERMISSOES:
            objetos.append(
                NivelAcessoPermissao(
                    nivel_acesso=nivel,
                    permissao=permissao,
                    ativo=permissao in ativas,
                )
            )
    NivelAcessoPermissao.objects.bulk_create(objetos)


def remove_permissoes(apps, schema_editor):
    NivelAcessoPermissao = apps.get_model("core", "NivelAcessoPermissao")
    NivelAcessoPermissao.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_ensure_cargo_departamento_columns'),
    ]

    operations = [
        migrations.CreateModel(
            name='NivelAcessoPermissao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nivel_acesso', models.CharField(choices=[('recepcionista', 'Recepcionista'), ('coordenacao', 'Coordenação'), ('super_admin', 'Super Admin')], max_length=20)),
                ('permissao', models.CharField(choices=[('checkin', 'Check-in e Atendimento'), ('prontuario', 'Edição de Prontuário'), ('usuarios', 'Gestão de Usuários'), ('auditoria', 'Auditoria de Logs'), ('deletar', 'Deletar Registros')], max_length=20)),
                ('ativo', models.BooleanField(default=False)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'permissão de nível de acesso',
                'verbose_name_plural': 'permissões de nível de acesso',
                'ordering': ('nivel_acesso', 'permissao'),
                'unique_together': {('nivel_acesso', 'permissao')},
            },
        ),
        migrations.RunPython(seed_permissoes, remove_permissoes),
    ]
