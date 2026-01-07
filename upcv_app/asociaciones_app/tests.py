from __future__ import annotations

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse

from .forms import ItemChecklistFormSet
from .models import Anio, Asociacion, AsociacionUsuario, ExpedienteCAIMUS, ResolucionExpediente


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
        expediente.items.create(numero=1, seccion=1, titulo="Doc", hint="")
        formset = ItemChecklistFormSet(
            data={
                "itemchecklistcaimus_set-TOTAL_FORMS": "1",
                "itemchecklistcaimus_set-INITIAL_FORMS": "1",
                "itemchecklistcaimus_set-MIN_NUM_FORMS": "0",
                "itemchecklistcaimus_set-MAX_NUM_FORMS": "1000",
                "itemchecklistcaimus_set-0-id": str(expediente.items.first().id),
                "itemchecklistcaimus_set-0-entregado": "on",
                "itemchecklistcaimus_set-0-observaciones": "",
            },
            instance=expediente,
        )
        self.assertFalse(formset.is_valid())
        self.assertIn("Debe adjuntar el PDF", str(formset.errors))

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
