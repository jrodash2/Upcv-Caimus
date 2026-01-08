from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("asociaciones_app", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="itemchecklistcaimus",
            constraint=models.CheckConstraint(
                check=models.Q(("seccion__in", [1, 2, 3])),
                name="itemchecklist_seccion_valida",
            ),
        ),
    ]
