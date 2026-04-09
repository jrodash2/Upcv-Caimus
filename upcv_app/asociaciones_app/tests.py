from __future__ import annotations

from datetime import date

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import (
    Anio,
    Asociacion,
    AsociacionUsuario,
    ChecklistAnioItem,
    ExpedienteCAIMUS,
    InformeMensual,
    ResolucionExpediente,
    crear_items_expediente,
)


class AsociacionesTests(TestCase):
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name="Administrador")
        self.admin_user = User.objects.create_user(username="admin", password="pass123")
        self.admin_user.groups.add(self.admin_group)

        self.asociacion_group, _ = Group.objects.get_or_create(name="Asociacion")
        self.user = User.objects.create_user(username="user1", password="pass123")
        self.user.groups.add(self.asociacion_group)

        self.anio = Anio.objects.create(anio=2026)
        self.asociacion = Asociacion.objects.create(anio=self.anio, nombre="Asociacion X", codigo="AX")
        self.asociacion_otra = Asociacion.objects.create(anio=self.anio, nombre="Asociacion Y", codigo="AY")

    def _crear_expediente_aprobado_completo(self):
        ChecklistAnioItem.objects.create(anio=self.anio, numero=1, titulo="Doc 1", activo=True)
        expediente = ExpedienteCAIMUS.objects.create(
            asociacion=self.asociacion,
            creado_por=self.admin_user,
            estado=ExpedienteCAIMUS.ESTADO_APROBADO,
        )
        crear_items_expediente(expediente)
        item = expediente.items.first()
        item.pdf = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        item.save()
        ResolucionExpediente.objects.create(
            expediente=expediente,
            correlativo="RES-2026-001",
            fecha_emision=date.today(),
            generado_por=self.admin_user,
            contenido_snapshot={"asociacion": self.asociacion.nombre},
        )
        return expediente

    def test_usuario_no_asignado_no_puede_ver_expediente(self):
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[self.asociacion.pk]))
        self.assertEqual(response.status_code, 403)

    def test_entregado_sin_pdf_es_invalido(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.user)
        item = expediente.items.create(numero=1, seccion=1, titulo="Doc", hint="")
        self.assertFalse(item.entregado)

    def test_no_permite_generar_resolucion_si_no_aprobado(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:resolucion_pdf", args=[expediente.pk]))
        self.assertEqual(response.status_code, 403)

    def test_admin_aprueba_crea_historial_y_correlativo(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.post(
            reverse("asociaciones:expediente_revision", args=[expediente.pk]),
            {"estado": ExpedienteCAIMUS.ESTADO_APROBADO, "observacion_admin": ""},
        )
        self.assertEqual(response.status_code, 302)
        expediente.refresh_from_db()
        self.assertEqual(expediente.estado, ExpedienteCAIMUS.ESTADO_APROBADO)
        self.assertEqual(expediente.historial_estados.count(), 1)
        resolucion = ResolucionExpediente.objects.get(expediente=expediente)
        self.assertIn(str(self.anio.anio), resolucion.correlativo)

    def test_no_asignado_no_puede_subir_ni_guardar_obs(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        item = expediente.items.create(numero=1, seccion=1, titulo="Doc", hint="")
        client = Client()
        client.login(username="user1", password="pass123")
        archivo = SimpleUploadedFile("test.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        response = client.post(
            reverse("asociaciones:item_upload", args=[expediente.pk, item.pk]),
            {"pdf": archivo},
        )
        self.assertEqual(response.status_code, 403)
        response = client.post(
            reverse("asociaciones:item_observacion", args=[expediente.pk, item.pk]),
            {"observaciones": "Nota"},
        )
        self.assertEqual(response.status_code, 403)

    def test_subir_pdf_sin_bloqueo_secciones(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.user)
        item_sec2 = expediente.items.create(numero=9, seccion=2, titulo="Doc 2", hint="")
        client = Client()
        client.login(username="user1", password="pass123")
        archivo = SimpleUploadedFile("test.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        response = client.post(
            reverse("asociaciones:item_upload", args=[expediente.pk, item_sec2.pk]),
            {"pdf": archivo},
        )
        self.assertEqual(response.status_code, 302)
        item_sec2.refresh_from_db()
        self.assertTrue(item_sec2.pdf)

    def test_subir_pdf_marca_entregado_y_reemplaza(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.user)
        item = expediente.items.create(numero=1, seccion=1, titulo="Doc", hint="", observaciones="Obs")
        client = Client()
        client.login(username="user1", password="pass123")
        archivo1 = SimpleUploadedFile("test1.pdf", b"%PDF-1.4 test1", content_type="application/pdf")
        client.post(reverse("asociaciones:item_upload", args=[expediente.pk, item.pk]), {"pdf": archivo1})
        item.refresh_from_db()
        self.assertTrue(item.entregado)
        self.assertTrue(item.pdf.name.endswith("test1.pdf"))
        archivo2 = SimpleUploadedFile("test2.pdf", b"%PDF-1.4 test2", content_type="application/pdf")
        client.post(reverse("asociaciones:item_upload", args=[expediente.pk, item.pk]), {"pdf": archivo2})
        item.refresh_from_db()
        self.assertTrue(item.pdf.name.endswith("test2.pdf"))
        self.assertEqual(item.observaciones, "Obs")

    def test_guardar_observacion_bloqueada(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.user)
        item_sec2 = expediente.items.create(numero=9, seccion=2, titulo="Doc 2", hint="")
        client = Client()
        client.login(username="user1", password="pass123")
        client.post(
            reverse("asociaciones:item_observacion", args=[expediente.pk, item_sec2.pk]),
            {"observaciones": "Nota"},
        )
        item_sec2.refresh_from_db()
        self.assertEqual(item_sec2.observaciones, "Nota")

    def test_asociacion_no_puede_acceder_vistas_admin(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:anios_list"))
        self.assertEqual(response.status_code, 403)
        response = client.get(reverse("asociaciones:asociacion_usuarios", args=[self.asociacion.pk]))
        self.assertEqual(response.status_code, 403)
        response = client.get(reverse("asociaciones:bandeja_revision"))
        self.assertEqual(response.status_code, 403)
        response = client.get(reverse("asociaciones:expediente_revision", args=[expediente.pk]))
        self.assertEqual(response.status_code, 403)

    def test_asociacion_puede_ver_mis_asociaciones(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:mis_asociaciones"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.asociacion.nombre)

    def test_asociacion_no_puede_ver_otra_asociacion(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[self.asociacion_otra.pk]))
        self.assertEqual(response.status_code, 403)

    def test_asociacion_no_puede_descargar_resolucion_sin_aprobacion(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:resolucion_pdf", args=[expediente.pk]))
        self.assertEqual(response.status_code, 403)

    def test_asociacion_puede_descargar_resolucion_aprobada(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        expediente = self._crear_expediente_aprobado_completo()
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:resolucion_pdf", args=[expediente.pk]))
        self.assertEqual(response.status_code, 200)

    def test_asociacion_no_puede_descargar_resolucion_si_expediente_incompleto(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        ChecklistAnioItem.objects.create(anio=self.anio, numero=1, titulo="Doc 1", activo=True)
        expediente = ExpedienteCAIMUS.objects.create(
            asociacion=self.asociacion,
            creado_por=self.admin_user,
            estado=ExpedienteCAIMUS.ESTADO_APROBADO,
        )
        crear_items_expediente(expediente)
        ResolucionExpediente.objects.create(
            expediente=expediente,
            correlativo="RES-2026-001",
            fecha_emision=date.today(),
            generado_por=self.admin_user,
            contenido_snapshot={"asociacion": self.asociacion.nombre},
        )
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:resolucion_pdf", args=[expediente.pk]))
        self.assertEqual(response.status_code, 403)

    def test_asociacion_ve_boton_descargar_si_aprobado_y_completo(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        expediente = self._crear_expediente_aprobado_completo()
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[expediente.asociacion.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Descargar Resolución PDF")

    def test_asociacion_no_ve_boton_descargar_si_falta_pdf(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        ChecklistAnioItem.objects.create(anio=self.anio, numero=1, titulo="Doc 1", activo=True)
        expediente = ExpedienteCAIMUS.objects.create(
            asociacion=self.asociacion,
            creado_por=self.admin_user,
            estado=ExpedienteCAIMUS.ESTADO_APROBADO,
        )
        crear_items_expediente(expediente)
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[expediente.asociacion.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Descargar Resolución PDF")

    def test_asociacion_no_ve_boton_descargar_si_no_aprobado(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        expediente = self._crear_expediente_aprobado_completo()
        expediente.estado = ExpedienteCAIMUS.ESTADO_EN_REVISION
        expediente.save(update_fields=["estado"])
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[expediente.asociacion.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Descargar Resolución PDF")

    def test_admin_no_ve_boton_descargar_resolucion(self):
        expediente = self._crear_expediente_aprobado_completo()
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[expediente.asociacion.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Descargar Resolución PDF")

    def test_asociacion_no_puede_ver_informes_otra_asociacion(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        InformeMensual.objects.create(asociacion=self.asociacion_otra, mes=1)
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:informes_mensuales", args=[self.asociacion_otra.pk]))
        self.assertEqual(response.status_code, 403)

    def test_asociacion_no_puede_aprobar_informe(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        informe = InformeMensual.objects.create(asociacion=self.asociacion, mes=1)
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.post(
            reverse("asociaciones:informe_estado", args=[self.asociacion.pk, informe.mes]),
            {"estado": InformeMensual.ESTADO_APROBADO},
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_puede_aprobar_informe(self):
        informe = InformeMensual.objects.create(asociacion=self.asociacion, mes=1)
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.post(
            reverse("asociaciones:informe_estado", args=[self.asociacion.pk, informe.mes]),
            {"estado": InformeMensual.ESTADO_APROBADO},
        )
        self.assertEqual(response.status_code, 302)
        informe.refresh_from_db()
        self.assertEqual(informe.estado, InformeMensual.ESTADO_APROBADO)

    def test_admin_puede_ver_y_guardar_checklist_anio(self):
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:anio_checklist", args=[self.anio.pk]))
        self.assertEqual(response.status_code, 200)

        payload = {
            "checklist-TOTAL_FORMS": "1",
            "checklist-INITIAL_FORMS": "0",
            "checklist-MIN_NUM_FORMS": "0",
            "checklist-MAX_NUM_FORMS": "1000",
            "checklist-0-id": "",
            "checklist-0-numero": "1",
            "checklist-0-titulo": "Documento nuevo",
            "checklist-0-descripcion": "Descripción de prueba",
            "checklist-0-activo": "on",
            "checklist-0-DELETE": "",
        }
        response = client.post(reverse("asociaciones:anio_checklist_guardar", args=[self.anio.pk]), payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ChecklistAnioItem.objects.filter(anio=self.anio, numero=1, titulo="Documento nuevo").exists())

    def test_usuario_asociacion_recibe_403_en_checklist_anio(self):
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:anio_checklist", args=[self.anio.pk]))
        self.assertEqual(response.status_code, 403)

    def test_crear_expediente_copia_items_del_anio(self):
        ChecklistAnioItem.objects.create(anio=self.anio, numero=1, titulo="Doc 1", descripcion="Desc", activo=True)
        ChecklistAnioItem.objects.create(anio=self.anio, numero=2, titulo="Doc 2", descripcion="", activo=True)
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        crear_items_expediente(expediente)
        self.assertEqual(expediente.items.count(), 2)
        self.assertTrue(expediente.items.filter(numero=1, titulo="Doc 1", plantilla_item__isnull=False).exists())

    def test_expediente_no_falla_si_anio_sin_checklist(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[self.asociacion.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(ChecklistAnioItem.objects.filter(anio=self.anio).count(), 1)

    def test_expediente_muestra_items_del_anio_correcto(self):
        anio_otro = Anio.objects.create(anio=2027)
        asociacion_otra = Asociacion.objects.create(anio=anio_otro, nombre="Asoc Z", codigo="AZ")
        ChecklistAnioItem.objects.create(anio=self.anio, numero=1, titulo="Doc Año 2026", activo=True)
        ChecklistAnioItem.objects.create(anio=anio_otro, numero=1, titulo="Doc Año 2027", activo=True)
        expediente = ExpedienteCAIMUS.objects.create(asociacion=asociacion_otra, creado_por=self.admin_user)
        crear_items_expediente(expediente)
        self.assertTrue(expediente.items.filter(titulo="Doc Año 2027").exists())
        self.assertFalse(expediente.items.filter(titulo="Doc Año 2026").exists())

    def test_subir_informe_pdf_marca_revision_y_conserva_observaciones(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=1,
            observaciones_usuario="Obs",
        )
        client = Client()
        client.login(username="user1", password="pass123")
        archivo = SimpleUploadedFile("informe.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        client.post(
            reverse("asociaciones:informe_upload", args=[self.asociacion.pk, informe.mes]),
            {"pdf": archivo},
        )
        informe.refresh_from_db()
        self.assertTrue(informe.pdf)
        self.assertEqual(informe.estado, InformeMensual.ESTADO_EN_REVISION)
        self.assertEqual(informe.observaciones_usuario, "Obs")
