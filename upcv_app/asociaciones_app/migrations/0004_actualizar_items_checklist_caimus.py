from django.db import migrations


def actualizar_items_checklist(apps, schema_editor):
    expediente_model = apps.get_model("asociaciones_app", "ExpedienteCAIMUS")
    item_model = apps.get_model("asociaciones_app", "ItemChecklistCAIMUS")
    checklist_items = [
        (1, "Solicitud dirigida al señor Ministro de Gobernación"),
        (2, "Plan Operativo Anual -POA-"),
        (3, "Copia legalizada del Testimonio de la Escritura Pública Constitutiva de la entidad"),
        (4, "Constancia de inscripción y actualización de datos -RTU-"),
        (5, "Solvencia Fiscal vigente"),
        (6, "Constancia de Inventario de Cuentas emitida por el Ministerio de Finanzas Públicas."),
        (
            7,
            "Certificación de la constancia de inscripción de la entidad en el Registro de Personas Jurídicas -REPEJU-",
        ),
        (8, "Copia legalizada -DPI- de representante legal"),
        (9, "Copia legalizada del Acta Notarial de nombramiento de representante legal"),
        (10, "Constancia de inscripción y actualización de datos -RTU- del representante legal"),
        (11, "Solvencia Fiscal vigente, del Representante Legal"),
        (12, "Certificación de la constancia de inscripción en el Registro de Personas Jurídicas -REPEJU-"),
    ]
    numeros_validos = {numero for numero, _titulo in checklist_items}

    for expediente in expediente_model.objects.all():
        existentes = {
            item.numero: item
            for item in item_model.objects.filter(expediente_id=expediente.pk)
        }
        for numero, titulo in checklist_items:
            item = existentes.get(numero)
            if item:
                item.titulo = titulo
                item.hint = ""
                item.seccion = 1
                item.save(update_fields=["titulo", "hint", "seccion"])
            else:
                item_model.objects.create(
                    expediente_id=expediente.pk,
                    numero=numero,
                    seccion=1,
                    titulo=titulo,
                    hint="",
                )
        item_model.objects.filter(expediente_id=expediente.pk).exclude(numero__in=numeros_validos).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("asociaciones_app", "0003_alter_itemchecklistcaimus_seccion_informemensual_and_more"),
    ]

    operations = [
        migrations.RunPython(actualizar_items_checklist, migrations.RunPython.noop),
    ]
