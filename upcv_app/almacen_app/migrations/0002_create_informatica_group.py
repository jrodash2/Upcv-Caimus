from django.db import migrations


def crear_grupo_informatica(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Informatica")


class Migration(migrations.Migration):

    dependencies = [
        ("almacen_app", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(crear_grupo_informatica, migrations.RunPython.noop),
    ]
