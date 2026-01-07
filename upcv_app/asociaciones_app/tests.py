from __future__ import annotations

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import Anio, Asociacion, AsociacionUsuario, ExpedienteCAIMUS, ItemChecklistCAIMUS, ResolucionExpediente


class AsociacionesTests(TestCase):
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name="Administrador")
        self.admin_user = User.objects.create_user(username="admin", password="pass123")
        self.admin_user.groups.add(self.admin_group)

        self.user = User.objects.create_user(username="user1", password="pass123")

        self.anio = Anio.objects.create(anio=2026)
        self.asociacion = Asociacion.objects.create(anio=self.anio, nombre="Asociacion X", codigo="AX")

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

    def test_bloqueo_secciones_no_permite_subir(self):
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
        self.assertFalse(item_sec2.pdf)

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
