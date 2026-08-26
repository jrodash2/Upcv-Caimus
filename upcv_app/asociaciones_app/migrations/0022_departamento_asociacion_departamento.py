from django.db import migrations, models
import django.db.models.deletion


DEPARTAMENTOS = [
    ("01", "Guatemala"), ("02", "El Progreso"), ("03", "Sacatepéquez"),
    ("04", "Chimaltenango"), ("05", "Escuintla"), ("06", "Santa Rosa"),
    ("07", "Sololá"), ("08", "Totonicapán"), ("09", "Quetzaltenango"),
    ("10", "Suchitepéquez"), ("11", "Retalhuleu"), ("12", "San Marcos"),
    ("13", "Huehuetenango"), ("14", "Quiché"), ("15", "Baja Verapaz"),
    ("16", "Alta Verapaz"), ("17", "Petén"), ("18", "Izabal"),
    ("19", "Zacapa"), ("20", "Chiquimula"), ("21", "Jalapa"),
    ("22", "Jutiapa"),
]


def cargar_departamentos(apps, schema_editor):
    Departamento = apps.get_model("asociaciones_app", "Departamento")
    for codigo, nombre in DEPARTAMENTOS:
        Departamento.objects.update_or_create(codigo=codigo, defaults={"nombre": nombre, "activo": True})


def eliminar_departamentos(apps, schema_editor):
    # Keep the reverse migration safe when associations were already assigned.
    pass


class Migration(migrations.Migration):
    dependencies = [("asociaciones_app", "0021_anio_acuerdo_gubernativo_anio_decreto_congreso")]
    operations = [
        migrations.CreateModel(
            name="Departamento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=100, unique=True)),
                ("codigo", models.CharField(max_length=2, unique=True)),
                ("activo", models.BooleanField(default=True)),
            ],
            options={"verbose_name": "Departamento", "verbose_name_plural": "Departamentos", "ordering": ["nombre"]},
        ),
        migrations.AddField(
            model_name="asociacion", name="departamento",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="asociaciones", to="asociaciones_app.departamento"),
        ),
        migrations.RunPython(cargar_departamentos, eliminar_departamentos),
    ]
