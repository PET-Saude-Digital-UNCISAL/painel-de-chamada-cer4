from django.db import migrations

# Migration de reparo (commit cce188a, 28/07/2026), nao de feature nova.
#
# A migration 0006 originalmente so atualizava o "state" do Django (via
# SeparateDatabaseAndState) sem criar as colunas cargo/departamento de
# verdade no banco. Ela foi corrigida no dia seguinte, mas essa correcao
# nao alcanca bancos que ja tinham rodado a versao quebrada -- pra eles, o
# django_migrations diz que a 0006 foi aplicada, mas as colunas nao
# existem.
#
# Por isso essa migration nao usa AddField normal: ela roda um
# "ADD COLUMN IF NOT EXISTS" via SQL direto, que funciona tanto em quem
# ja tinha as colunas (idempotente, nao faz nada) quanto em quem ficou
# com o banco desincronizado por causa do bug da 0006.


def _add_column_if_not_exists(table, column, col_def, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        engine = schema_editor.connection.vendor
        if engine == "postgresql":
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_def}"
            )
        else:
            try:
                cursor.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"
                )
            except Exception:
                pass


def ensure_columns(apps, schema_editor):
    columns = {
        "cargo": "varchar(100) NOT NULL DEFAULT ''",
        "departamento": "varchar(100) NOT NULL DEFAULT ''",
    }
    for column, col_def in columns.items():
        _add_column_if_not_exists("core_usuariosistema", column, col_def, schema_editor)


def reverse_ensure_columns(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_encaixepaciente_ausente_em_and_more"),
    ]

    operations = [
        migrations.RunPython(ensure_columns, reverse_ensure_columns),
    ]
