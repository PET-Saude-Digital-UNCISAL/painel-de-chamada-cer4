from django.db import migrations


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