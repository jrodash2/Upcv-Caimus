from __future__ import annotations

from datetime import date
from io import BytesIO

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from .forms import AsociacionUsuarioForm
from .models import (
    Anio,
    Asociacion,
    AsociacionUsuario,
    ChecklistAnioItem,
    ExpedienteCAIMUS,
    EntradaRevisionAdmin,
    InformeMensual,
    HistorialItemExpediente,
    NotificacionAdmin,
    NotificacionAsociacion,
    ResolucionInformeMensual,
    ResolucionExpediente,
    ItemChecklistCAIMUS,
    crear_items_expediente,
    ConfiguracionInformeAnio,
    Departamento,
)
from .permissions import expediente_items_100_aprobados


class AsociacionesTests(TestCase):
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name="Administrador")
        self.admin_user = User.objects.create_user(username="admin", password="pass123")
        self.admin_user.groups.add(self.admin_group)

        self.informatica_group, _ = Group.objects.get_or_create(name="Informatica")
        self.informatica_user = User.objects.create_user(username="informatica", password="pass123")
        self.informatica_user.groups.add(self.informatica_group)

        self.asociacion_group, _ = Group.objects.get_or_create(name="Asociacion")
        self.user = User.objects.create_user(username="user1", password="pass123")
        self.user.groups.add(self.asociacion_group)

        self.anio = Anio.objects.create(anio=2026)
        self.anio_otro = Anio.objects.create(anio=2027)
        self.asociacion = Asociacion.objects.create(anio=self.anio, nombre="Asociacion X", codigo="AX")
        self.asociacion_otra = Asociacion.objects.create(anio=self.anio, nombre="Asociacion Y", codigo="AY")
        self.asociacion_otro_anio = Asociacion.objects.create(anio=self.anio_otro, nombre="Asociacion Z", codigo="AZ")

    def test_mapa_publico_agrupa_por_departamento_y_enlaza_mismo_detalle(self):
        guatemala = Departamento.objects.get(codigo="01")
        self.asociacion.departamento = guatemala
        self.asociacion.save(update_fields=["departamento"])

        response = Client().get(reverse("asociaciones_publicas"), {"anio": 2026})

        departamento = next(item for item in response.context["departamentos_publicos"] if item["codigo"] == "01")
        self.assertEqual(departamento["cantidad"], 1)
        self.assertEqual(departamento["asociaciones"][0]["nombre"], "Asociacion X")
        self.assertEqual(
            departamento["asociaciones"][0]["detalle_url"],
            reverse("asociacion_publica_detalle", args=[self.asociacion.pk]),
        )

    def test_mapa_incluye_departamentos_vacios_y_omite_asociaciones_sin_departamento(self):
        response = Client().get(reverse("asociaciones_publicas"), {"anio": 2026})
        self.assertEqual(len(response.context["departamentos_publicos"]), 22)
        self.assertTrue(all(item["cantidad"] == 0 for item in response.context["departamentos_publicos"]))
        self.assertEqual(response.content.count(b'class="gt-department"'), 22)
        self.assertContains(response, 'class="guatemala-interactive-map"')
        self.assertContains(response, 'id="departamentos-publicos"')
        self.assertContains(response, 'path.parentNode.appendChild(path)')

    def test_mapa_respeta_el_anio_seleccionado(self):
        peten = Departamento.objects.get(codigo="17")
        self.asociacion.departamento = peten
        self.asociacion.save(update_fields=["departamento"])
        self.asociacion_otro_anio.departamento = peten
        self.asociacion_otro_anio.save(update_fields=["departamento"])

        response_2026 = Client().get(reverse("asociaciones_publicas"), {"anio": 2026})
        response_2027 = Client().get(reverse("asociaciones_publicas"), {"anio": 2027})
        peten_2026 = next(item for item in response_2026.context["departamentos_publicos"] if item["codigo"] == "17")
        peten_2027 = next(item for item in response_2027.context["departamentos_publicos"] if item["codigo"] == "17")
        self.assertEqual([item["nombre"] for item in peten_2026["asociaciones"]], ["Asociacion X"])
        self.assertEqual([item["nombre"] for item in peten_2027["asociaciones"]], ["Asociacion Z"])

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

    def test_portal_publico_no_requiere_login_y_no_expone_datos_sensibles(self):
        self.asociacion.dpi_representante_legal = "1234567890101"
        self.asociacion.save(update_fields=["dpi_representante_legal"])
        expediente = ExpedienteCAIMUS.objects.create(
            asociacion=self.asociacion,
            estado=ExpedienteCAIMUS.ESTADO_EN_REVISION,
            observacion_admin="Observación estrictamente interna",
        )
        expediente.items.create(numero=1, titulo="Requisito público", observaciones="Dato privado")

        response = Client().get(reverse("asociaciones_publicas"), {"anio": 2026})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Asociacion X")
        self.assertContains(response, "Sin asignar")
        self.assertNotContains(response, "1234567890101")
        self.assertNotContains(response, "Observación estrictamente interna")
        self.assertNotContains(response, "Dato privado")

    def test_portal_publico_oculta_seccion_legal_sin_documentos(self):
        response = Client().get(reverse("asociaciones_publicas"), {"anio": 2026})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Documentos legales del ejercicio fiscal")

    def test_portal_publico_sin_anio_selecciona_activo_mas_reciente(self):
        self.anio_otro.decreto_congreso = SimpleUploadedFile("decreto-2027.pdf", b"%PDF-1.4 d")
        self.anio_otro.save()

        response = Client().get(reverse("asociaciones:asociaciones_publicas"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["anio_seleccionado"], 2027)
        self.assertEqual(response.context["anio_obj"], self.anio_otro)
        self.assertContains(response, "Documentos legales del ejercicio fiscal 2027")
        self.assertContains(response, "Decreto del Congreso")

    def test_portal_publico_anio_invalido_usa_activo_mas_reciente(self):
        response = Client().get(reverse("asociaciones:asociaciones_publicas"), {"anio": "abc"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["anio_seleccionado"], 2027)
        self.assertEqual(response.context["anio_obj"], self.anio_otro)

    def test_portal_publico_sin_activos_usa_anio_mas_reciente(self):
        Anio.objects.update(activo=False)

        response = Client().get(reverse("asociaciones:asociaciones_publicas"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["anio_seleccionado"], 2027)
        self.assertEqual(response.context["anio_obj"], self.anio_otro)

    def test_portal_publico_muestra_solamente_acuerdo_disponible(self):
        self.anio.acuerdo_gubernativo = SimpleUploadedFile(
            "acuerdo.pdf", b"%PDF-1.4 acuerdo", content_type="application/pdf"
        )
        self.anio.save()
        response = Client().get(reverse("asociaciones_publicas"), {"anio": 2026})
        self.assertEqual(response.context["anio_seleccionado"], 2026)
        self.assertEqual(response.context["anio_obj"], self.anio)
        self.assertContains(response, "Documentos legales del ejercicio fiscal 2026")
        self.assertContains(response, "Acuerdo gubernativo")
        self.assertNotContains(response, "Decreto del Congreso")

    def test_portal_publico_muestra_solamente_decreto_disponible(self):
        self.anio.decreto_congreso = SimpleUploadedFile(
            "decreto.pdf", b"%PDF-1.4 decreto", content_type="application/pdf"
        )
        self.anio.save()
        response = Client().get(reverse("asociaciones_publicas"), {"anio": 2026})
        self.assertContains(response, "Decreto del Congreso")
        self.assertNotContains(response, "Acuerdo gubernativo")

    def test_portal_publico_cambia_ambos_documentos_con_el_anio(self):
        self.anio.acuerdo_gubernativo = SimpleUploadedFile("acuerdo-2026.pdf", b"%PDF-1.4 a")
        self.anio.decreto_congreso = SimpleUploadedFile("decreto-2026.pdf", b"%PDF-1.4 d")
        self.anio.save()
        self.anio_otro.decreto_congreso = SimpleUploadedFile("decreto-2027.pdf", b"%PDF-1.4 d")
        self.anio_otro.save()

        response_2026 = Client().get(reverse("asociaciones_publicas"), {"anio": 2026})
        self.assertContains(response_2026, "Acuerdo gubernativo")
        self.assertContains(response_2026, "Decreto del Congreso")
        response_2027 = Client().get(reverse("asociaciones_publicas"), {"anio": 2027})
        self.assertEqual(response_2027.context["anio_seleccionado"], 2027)
        self.assertEqual(response_2027.context["anio_obj"], self.anio_otro)
        self.assertNotContains(response_2027, "Acuerdo gubernativo")
        self.assertContains(response_2027, "Decreto del Congreso")

    def test_detalle_publico_usa_documentos_del_anio_de_la_asociacion(self):
        self.anio.acuerdo_gubernativo = SimpleUploadedFile("acuerdo-2026.pdf", b"%PDF-1.4 a")
        self.anio.save()
        self.anio_otro.decreto_congreso = SimpleUploadedFile("decreto-2027.pdf", b"%PDF-1.4 d")
        self.anio_otro.save()

        response = Client().get(reverse("asociacion_publica_detalle", args=[self.asociacion.pk]))

        self.assertEqual(response.context["anio_seleccionado"], 2026)
        self.assertEqual(response.context["anio_obj"], self.asociacion.anio)
        self.assertContains(response, "Marco legal del ejercicio fiscal 2026")
        self.assertContains(response, "Acuerdo gubernativo")
        self.assertNotContains(response, "Decreto del Congreso")

    def test_documento_legal_publico_solo_sirve_campos_permitidos(self):
        self.anio.acuerdo_gubernativo = SimpleUploadedFile("acuerdo.pdf", b"%PDF-1.4 acuerdo")
        self.anio.save()
        response = Client().get(reverse("documento_legal_publico", args=[self.anio.pk, "acuerdo"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(
            Client().get(reverse("documento_legal_publico", args=[self.anio.pk, "interno"])).status_code,
            404,
        )

    def test_dashboard_informatica_muestra_enlace_publico_absoluto(self):
        client = Client()
        client.login(username="informatica", password="pass123")

        response = client.get(reverse("asociaciones:dashboard"))

        self.assertEqual(response.status_code, 200)
        url_publica = response.wsgi_request.build_absolute_uri(
            reverse("asociaciones:asociaciones_publicas")
        )
        self.assertEqual(response.context["url_publica"], url_publica)
        self.assertContains(response, 'id="copiarLinkPublico"')
        self.assertContains(response, url_publica)

    def test_dashboard_no_muestra_enlace_publico_a_otros_grupos(self):
        for usuario in (self.admin_user, self.user):
            with self.subTest(usuario=usuario.username):
                client = Client()
                client.force_login(usuario)
                response = client.get(reverse("asociaciones:dashboard"))
                self.assertNotIn(b'id="copiarLinkPublico"', response.content)

    def test_correlativo_publico_solo_aparece_con_aprobacion_completa(self):
        expediente = ExpedienteCAIMUS.objects.create(
            asociacion=self.asociacion,
            estado=ExpedienteCAIMUS.ESTADO_APROBADO,
        )
        item = expediente.items.create(
            numero=1,
            titulo="Requisito público",
            estado_item=ItemChecklistCAIMUS.ESTADO_APROBADO,
        )
        ResolucionExpediente.objects.create(
            expediente=expediente,
            correlativo="UPCV-CAIMUS-2026-0001",
            fecha_emision=date.today(),
        )
        url = reverse("asociacion_publica_detalle", args=[self.asociacion.pk])

        response = Client().get(url)
        self.assertContains(response, "UPCV-CAIMUS-2026-0001")
        self.assertContains(response, "Expediente aprobado")

        item.estado_item = ItemChecklistCAIMUS.ESTADO_BORRADOR
        item.save(update_fields=["estado_item"])
        response = Client().get(url)
        self.assertContains(response, "Sin asignar")
        self.assertNotContains(response, "UPCV-CAIMUS-2026-0001")

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

    def test_subir_excel_xlsy_xlsx_permitido(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.user)
        item = expediente.items.create(numero=1, seccion=1, titulo="Doc", hint="")
        client = Client()
        client.login(username="user1", password="pass123")

        archivo_xls = SimpleUploadedFile("presupuesto.xls", b"excel-binario", content_type="application/vnd.ms-excel")
        response_xls = client.post(reverse("asociaciones:item_upload", args=[expediente.pk, item.pk]), {"pdf": archivo_xls})
        self.assertEqual(response_xls.status_code, 302)
        item.refresh_from_db()
        self.assertTrue(item.pdf.name.endswith("presupuesto.xls"))
        self.assertTrue(item.entregado)

        archivo_xlsx = SimpleUploadedFile(
            "presupuesto.xlsx",
            b"excel-openxml",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response_xlsx = client.post(reverse("asociaciones:item_upload", args=[expediente.pk, item.pk]), {"pdf": archivo_xlsx})
        self.assertEqual(response_xlsx.status_code, 302)
        item.refresh_from_db()
        self.assertTrue(item.pdf.name.endswith("presupuesto.xlsx"))
        self.assertTrue(item.entregado)

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

    def test_administrador_puede_acceder_vistas_operativas_por_url_directa(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        client = Client()
        client.login(username="admin", password="pass123")

        rutas = [
            reverse("asociaciones:inicio"),
            reverse("asociaciones:dashboard"),
            reverse("asociaciones:anios_list"),
            reverse("asociaciones:anio_checklist", args=[self.anio.pk]),
            reverse("asociaciones:anio_informes_config", args=[self.anio.pk]),
            reverse("asociaciones:asociacion_list", args=[self.anio.pk]),
            reverse("asociaciones:asociacion_usuarios", args=[self.asociacion.pk]),
            reverse("asociaciones:asignaciones_list"),
            reverse("asociaciones:bandeja_revision"),
            reverse("asociaciones:expediente_revision", args=[expediente.pk]),
        ]

        for ruta in rutas:
            with self.subTest(ruta=ruta):
                response = client.get(ruta)
                self.assertEqual(response.status_code, 200)

    def test_administrador_no_ve_menu_configuracion(self):
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:anios_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "Asociaciones")
        self.assertContains(response, "Años")
        self.assertContains(response, "Asignaciones")
        self.assertNotContains(response, "Configuración")

    def test_informatica_ve_menu_configuracion(self):
        client = Client()
        client.login(username="informatica", password="pass123")
        response = client.get(reverse("asociaciones:anios_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Configuración")
        self.assertContains(response, "Usuarios")
        self.assertContains(response, "Institución")

    def test_asociacion_puede_ver_mis_asociaciones(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:mis_asociaciones"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.asociacion.nombre)
        self.assertNotContains(response, self.asociacion_otra.nombre)

    def test_vista_asignaciones_no_muestra_select_de_asociacion(self):
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:asociacion_usuarios", args=[self.asociacion.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"{self.asociacion.nombre} ({self.asociacion.anio.anio})")
        self.assertNotContains(response, 'name="asociacion"')
        self.assertNotContains(response, self.asociacion_otro_anio.nombre)

    def test_asignacion_usuario_se_guarda_siempre_en_asociacion_actual(self):
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.post(
            reverse("asociaciones:asociacion_usuarios", args=[self.asociacion.pk]),
            {
                "usuario": self.user.pk,
                "rol_en_asociacion": "Técnico",
                "activo": "on",
                "asociacion": self.asociacion_otro_anio.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        asignacion = AsociacionUsuario.objects.get(usuario=self.user)
        self.assertEqual(asignacion.asociacion, self.asociacion)

    def test_select_usuario_muestra_nombre_username_y_grupos(self):
        grupo_compras, _ = Group.objects.get_or_create(name="Compras")
        usuario_grupos = User.objects.create_user(
            username="mgarcia",
            password="pass123",
            first_name="María",
            last_name="García",
        )
        usuario_grupos.groups.add(grupo_compras, self.asociacion_group)
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:asociacion_usuarios", args=[self.asociacion.pk]))
        self.assertEqual(response.status_code, 200)

    def test_progress_aprobados_cero(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        expediente.items.create(numero=1, seccion=1, titulo="Doc 1", hint="", activo=True)
        expediente.items.create(numero=2, seccion=1, titulo="Doc 2", hint="", activo=True)
        stats = expediente.progress_stats()
        self.assertEqual(stats["approved_percent"], 0)

    def test_progress_aprobados_total(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        expediente.items.create(numero=1, seccion=1, titulo="Doc 1", hint="", activo=True, estado_item=ItemChecklistCAIMUS.ESTADO_APROBADO)
        expediente.items.create(numero=2, seccion=1, titulo="Doc 2", hint="", activo=True, estado_item=ItemChecklistCAIMUS.ESTADO_APROBADO)
        stats = expediente.progress_stats()
        self.assertEqual(stats["approved_percent"], 100)

    def test_progress_aprobados_parcial(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        expediente.items.create(numero=1, seccion=1, titulo="Doc 1", hint="", activo=True, estado_item=ItemChecklistCAIMUS.ESTADO_APROBADO)
        expediente.items.create(numero=2, seccion=1, titulo="Doc 2", hint="", activo=True)
        expediente.items.create(numero=3, seccion=1, titulo="Doc 3", hint="", activo=True)
        stats = expediente.progress_stats()
        self.assertEqual(stats["approved_percent"], 33)

    def test_timeline_revision_renderiza_estado_y_usuario(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        item = expediente.items.create(numero=1, seccion=1, titulo="Solicitud", hint="", activo=True, estado_item=ItemChecklistCAIMUS.ESTADO_APROBADO)
        item.aprobado_por = self.admin_user
        item.fecha_aprobacion = timezone.now()
        item.save(update_fields=["aprobado_por", "fecha_aprobacion"])
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[self.asociacion.pk]))
        self.assertContains(response, "Timeline de revisión")
        self.assertContains(response, "Solicitud")
        self.assertContains(response, "Aprobado por")
        self.assertContains(response, "admin")

    def test_vista_expediente_no_falla_sin_items(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        expediente.items.all().delete()
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[self.asociacion.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0%")

    def test_helper_items_100_aprobados_exige_items_y_estado_aprobado(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        self.assertFalse(expediente_items_100_aprobados(expediente))
        expediente.items.create(numero=1, seccion=1, titulo="Doc 1", hint="", activo=True)
        self.assertFalse(expediente_items_100_aprobados(expediente))
        expediente.items.filter(numero=1).update(estado_item=ItemChecklistCAIMUS.ESTADO_APROBADO)
        self.assertTrue(expediente_items_100_aprobados(expediente))

    def test_expediente_aprobado_inconsistente_se_muestra_en_revision(self):
        expediente = ExpedienteCAIMUS.objects.create(
            asociacion=self.asociacion,
            creado_por=self.admin_user,
            estado=ExpedienteCAIMUS.ESTADO_APROBADO,
        )
        expediente.items.create(numero=1, seccion=1, titulo="Doc 1", hint="", activo=True)
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[self.asociacion.pk]))
        self.assertContains(response, "Pendiente de aprobación de ítems")

    def test_no_permite_aprobar_expediente_si_faltan_pdfs_o_aprobaciones(self):
        expediente = ExpedienteCAIMUS.objects.create(
            asociacion=self.asociacion,
            creado_por=self.admin_user,
            estado=ExpedienteCAIMUS.ESTADO_EN_REVISION,
        )
        expediente.items.create(
            numero=1,
            seccion=1,
            titulo="Doc 1",
            hint="",
            activo=True,
            estado_item=ItemChecklistCAIMUS.ESTADO_APROBADO,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.post(
            reverse("asociaciones:expediente_revision", args=[expediente.pk]),
            {"estado": ExpedienteCAIMUS.ESTADO_APROBADO, "observacion_admin": ""},
            follow=True,
        )
        expediente.refresh_from_db()
        self.assertNotEqual(expediente.estado, ExpedienteCAIMUS.ESTADO_APROBADO)
        self.assertContains(response, "No es posible aprobar el expediente. Aún existen ítems pendientes de aprobación.")

    def test_select_usuario_sin_nombre_muestra_username_y_sin_grupo(self):
        usuario_sin_grupo = User.objects.create_user(username="sin_grupo", password="pass123")
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:asociacion_usuarios", args=[self.asociacion.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"{usuario_sin_grupo.username} — Sin grupo")

    def test_queryset_usuario_prefetch_groups(self):
        form = AsociacionUsuarioForm(asociacion_actual=self.asociacion)
        self.assertIn("groups", getattr(form.fields["usuario"].queryset, "_prefetch_related_lookups", ()))

    def test_asociacion_no_puede_ver_otra_asociacion(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[self.asociacion_otra.pk]))
        self.assertEqual(response.status_code, 403)

    def test_admin_puede_ver_dashboard_global(self):
        ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        ExpedienteCAIMUS.objects.create(asociacion=self.asociacion_otra, creado_por=self.admin_user)
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard de asociaciones")
        self.assertContains(response, self.asociacion.nombre)
        self.assertContains(response, self.asociacion_otra.nombre)

    def test_admin_inicio_modulo_muestra_dashboard(self):
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:inicio"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard de asociaciones")

    def test_admin_dashboard_principal_redirige_a_dashboard_asociaciones(self):
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("almacen:dahsboard"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("asociaciones:inicio"))

    def test_dashboard_admin_no_muestra_link_redundante_dashboard_asociaciones(self):
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:inicio"))
        self.assertEqual(response.status_code, 200)

    def test_admin_puede_configurar_informes_anio(self):
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.post(reverse("asociaciones:anio_informes_config", args=[self.anio.pk]), {"mes_requerido": ["1", "2"]})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ConfiguracionInformeAnio.objects.get(anio=self.anio, mes=1).requerido)
        self.assertFalse(ConfiguracionInformeAnio.objects.get(anio=self.anio, mes=3).requerido)

    def test_asociacion_no_puede_entrar_config_informes(self):
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:anio_informes_config", args=[self.anio.pk]))
        self.assertEqual(response.status_code, 403)

    def test_mes_no_requerido_no_permite_enviar_revision(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        InformeMensual.objects.create(asociacion=self.asociacion, mes=1, creado_por=self.user, actualizado_por=self.user)
        ConfiguracionInformeAnio.objects.create(anio=self.anio, mes=1, requerido=False, actualizado_por=self.admin_user)
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.post(reverse("asociaciones:informe_enviar_revision", args=[self.asociacion.pk, 1]))
        self.assertEqual(response.status_code, 302)
        informe = InformeMensual.objects.get(asociacion=self.asociacion, mes=1)
        self.assertEqual(informe.estado, InformeMensual.ESTADO_BORRADOR)

    def test_mes_no_requerido_no_permite_subir_ni_observacion(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        ConfiguracionInformeAnio.objects.create(anio=self.anio, mes=2, requerido=False, actualizado_por=self.admin_user)
        client = Client()
        client.login(username="user1", password="pass123")
        archivo = SimpleUploadedFile("test.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        response_upload = client.post(reverse("asociaciones:informe_upload_narrativo", args=[self.asociacion.pk, 2]), {"pdf": archivo})
        response_obs = client.post(reverse("asociaciones:informe_observacion", args=[self.asociacion.pk, 2]), {"observaciones": "x"})
        self.assertEqual(response_upload.status_code, 302)
        self.assertEqual(response_obs.status_code, 302)
        self.assertNotContains(response, "Dashboard asociaciones")

    def test_usuario_asociacion_dashboard_solo_datos_propios(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        ExpedienteCAIMUS.objects.create(asociacion=self.asociacion_otra, creado_por=self.admin_user)
        NotificacionAsociacion.objects.create(asociacion=self.asociacion, titulo="Visible", mensaje="ok")
        NotificacionAsociacion.objects.create(asociacion=self.asociacion_otra, titulo="Oculta", mensaje="no")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mi dashboard de asociaciones")
        self.assertContains(response, "Visible")
        self.assertNotContains(response, "Oculta")

    def test_usuario_asociacion_inicio_modulo_muestra_dashboard_propio(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:inicio"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mi dashboard de asociaciones")

    def test_dashboard_metricas_cargan_sin_error(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mis asociaciones")
        self.assertContains(response, "Alertas nuevas")

    def test_observacion_admin_expediente_se_guarda_y_usuario_asociacion_la_ve(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        client_admin = Client()
        client_admin.login(username="admin", password="pass123")
        response = client_admin.post(
            reverse("asociaciones:expediente_revision", args=[expediente.pk]),
            {"estado": ExpedienteCAIMUS.ESTADO_RECHAZADO, "observacion_admin": "Falta firma del representante."},
        )
        self.assertEqual(response.status_code, 302)
        expediente.refresh_from_db()
        self.assertEqual(expediente.observacion_admin, "Falta firma del representante.")

        client_asoc = Client()
        client_asoc.login(username="user1", password="pass123")
        response = client_asoc.get(reverse("asociaciones:expediente_caimus", args=[self.asociacion.pk]))
        self.assertContains(response, "Observación del administrador")
        self.assertContains(response, "Falta firma del representante.")

    def test_observacion_admin_informe_se_guarda_y_usuario_asociacion_la_ve(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=3,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            archivo_presupuestario=SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_EN_REVISION,
        )
        client_admin = Client()
        client_admin.login(username="admin", password="pass123")
        response = client_admin.post(
            reverse("asociaciones:informe_estado", args=[self.asociacion.pk, informe.mes]),
            {"estado": InformeMensual.ESTADO_RECHAZADO, "observacion_admin": "Actualizar cuadro presupuestario."},
        )
        self.assertEqual(response.status_code, 302)
        informe.refresh_from_db()
        self.assertEqual(informe.observacion_admin, "Actualizar cuadro presupuestario.")

        client_asoc = Client()
        client_asoc.login(username="user1", password="pass123")
        response = client_asoc.get(reverse("asociaciones:informes_mensuales", args=[self.asociacion.pk]))
        self.assertContains(response, "Actualizar cuadro presupuestario.")

    def test_notificacion_observacion_expediente_solo_si_hay_cambio_real(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        client = Client()
        client.login(username="admin", password="pass123")
        client.post(
            reverse("asociaciones:expediente_revision", args=[expediente.pk]),
            {"estado": ExpedienteCAIMUS.ESTADO_RECHAZADO, "observacion_admin": "Corregir documento 4."},
        )
        client.post(
            reverse("asociaciones:expediente_revision", args=[expediente.pk]),
            {"estado": ExpedienteCAIMUS.ESTADO_RECHAZADO, "observacion_admin": "Corregir documento 4."},
        )
        self.assertEqual(
            NotificacionAsociacion.objects.filter(
                asociacion=self.asociacion,
                titulo="Nueva observación en expediente",
            ).count(),
            1,
        )

    def test_notificacion_observacion_informe_se_crea_para_asociacion_correcta(self):
        informe_a = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=4,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            archivo_presupuestario=SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_EN_REVISION,
        )
        InformeMensual.objects.create(
            asociacion=self.asociacion_otra,
            mes=4,
            archivo_narrativo=SimpleUploadedFile("narrativo2.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            archivo_presupuestario=SimpleUploadedFile("presupuestario2.pdf", b"%PDF-1.4 pre", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_EN_REVISION,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        client.post(
            reverse("asociaciones:informe_estado", args=[self.asociacion.pk, informe_a.mes]),
            {"estado": InformeMensual.ESTADO_RECHAZADO, "observacion_admin": "Detalle actualizado."},
        )
        self.assertTrue(
            NotificacionAsociacion.objects.filter(
                asociacion=self.asociacion,
                titulo="Nueva observación en informe mensual",
            ).exists()
        )
        self.assertFalse(
            NotificacionAsociacion.objects.filter(
                asociacion=self.asociacion_otra,
                titulo="Nueva observación en informe mensual",
            ).exists()
        )

    def test_usuario_asociacion_no_accede_dashboard_admin_principal(self):
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("almacen:dahsboard"))
        self.assertEqual(response.status_code, 403)

    def test_usuario_asociacion_puede_enviar_expediente_completo_a_revision(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        ChecklistAnioItem.objects.create(anio=self.anio, numero=1, titulo="Doc 1", activo=True)
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.user)
        crear_items_expediente(expediente)
        item = expediente.items.first()
        item.pdf = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        item.save()
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.post(reverse("asociaciones:expediente_enviar_revision", args=[self.asociacion.pk]))
        self.assertEqual(response.status_code, 302)
        expediente.refresh_from_db()
        self.assertEqual(expediente.estado, ExpedienteCAIMUS.ESTADO_EN_REVISION)

    def test_usuario_asociacion_no_puede_enviar_expediente_incompleto_a_revision(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        ChecklistAnioItem.objects.create(anio=self.anio, numero=1, titulo="Doc 1", activo=True)
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.user)
        crear_items_expediente(expediente)
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.post(reverse("asociaciones:expediente_enviar_revision", args=[self.asociacion.pk]))
        self.assertEqual(response.status_code, 302)
        expediente.refresh_from_db()
        self.assertEqual(expediente.estado, ExpedienteCAIMUS.ESTADO_BORRADOR)

    def test_usuario_asociacion_puede_enviar_informe_completo_a_revision(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=8,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            archivo_presupuestario=SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_BORRADOR,
        )
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.post(reverse("asociaciones:informe_enviar_revision", args=[self.asociacion.pk, informe.mes]))
        self.assertEqual(response.status_code, 302)
        informe.refresh_from_db()
        self.assertEqual(informe.estado, InformeMensual.ESTADO_EN_REVISION)

    def test_usuario_asociacion_no_puede_enviar_informe_incompleto_a_revision(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=9,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_BORRADOR,
        )
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.post(reverse("asociaciones:informe_enviar_revision", args=[self.asociacion.pk, informe.mes]))
        self.assertEqual(response.status_code, 302)
        informe.refresh_from_db()
        self.assertNotEqual(informe.estado, InformeMensual.ESTADO_EN_REVISION)

    def test_enviar_informe_a_revision_crea_alerta_admin(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=10,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            archivo_presupuestario=SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf"),
        )
        client = Client()
        client.login(username="user1", password="pass123")
        client.post(reverse("asociaciones:informe_enviar_revision", args=[self.asociacion.pk, informe.mes]))
        self.assertTrue(
            NotificacionAdmin.objects.filter(
                titulo="Informe enviado a revisión",
                asociacion=self.asociacion,
                informe=informe,
            ).exists()
        )
        alerta = NotificacionAdmin.objects.get(
            titulo="Informe enviado a revisión",
            asociacion=self.asociacion,
            informe=informe,
        )
        self.assertIn(f"#informe-mes-{informe.mes}", alerta.enlace)
        self.assertTrue(
            EntradaRevisionAdmin.objects.filter(
                tipo=EntradaRevisionAdmin.TIPO_INFORME,
                informe=informe,
                estado=EntradaRevisionAdmin.ESTADO_PENDIENTE,
            ).exists()
        )

    def test_enviar_expediente_a_revision_crea_alerta_admin(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        ChecklistAnioItem.objects.create(anio=self.anio, numero=1, titulo="Doc 1", activo=True)
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.user)
        crear_items_expediente(expediente)
        item = expediente.items.first()
        item.pdf = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        item.save()
        client = Client()
        client.login(username="user1", password="pass123")
        client.post(reverse("asociaciones:expediente_enviar_revision", args=[self.asociacion.pk]))
        self.assertTrue(
            NotificacionAdmin.objects.filter(
                titulo="Expediente enviado a revisión",
                asociacion=self.asociacion,
            ).exists()
        )
        self.assertTrue(
            EntradaRevisionAdmin.objects.filter(
                tipo=EntradaRevisionAdmin.TIPO_EXPEDIENTE,
                expediente=expediente,
                estado=EntradaRevisionAdmin.ESTADO_PENDIENTE,
            ).exists()
        )

    def test_dashboard_admin_muestra_alertas_pendientes(self):
        EntradaRevisionAdmin.objects.create(
            tipo=EntradaRevisionAdmin.TIPO_INFORME,
            titulo="Informe enviado a revisión",
            mensaje="Pendiente revisar informe.",
            asociacion=self.asociacion,
            enlace=reverse("asociaciones:informes_mensuales", args=[self.asociacion.pk]),
            estado=EntradaRevisionAdmin.ESTADO_PENDIENTE,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alertas nuevas")
        self.assertContains(response, "No hay alertas nuevas.")

    def test_dashboard_admin_muestra_total_alertas_no_leidas(self):
        NotificacionAdmin.objects.create(
            titulo="Alerta nueva",
            mensaje="Pendiente de revisar",
            asociacion=self.asociacion,
            leida=False,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alertas nuevas")
        self.assertContains(response, "1 nuevas")
        self.assertContains(response, "Alerta nueva")

    def test_dashboard_admin_no_renderiza_card_requieren_revision(self):
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Requieren revisión")

    def test_dashboard_y_bandeja_comparten_total_pendientes(self):
        EntradaRevisionAdmin.objects.create(
            tipo=EntradaRevisionAdmin.TIPO_INFORME,
            titulo="Informe pendiente",
            mensaje="Pendiente",
            asociacion=self.asociacion,
            estado=EntradaRevisionAdmin.ESTADO_PENDIENTE,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        dashboard = client.get(reverse("asociaciones:dashboard"), {"anio": self.anio.anio})
        bandeja = client.get(reverse("asociaciones:bandeja_revision"), {"anio": self.anio.pk, "estado": "pendiente"})
        self.assertContains(dashboard, "Alertas nuevas")
        self.assertContains(bandeja, "1 pendientes")

    def test_bandeja_muestra_estado_vacio(self):
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:bandeja_revision"), {"estado": "pendiente"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No hay pendientes de revisión.")

    def test_admin_ve_bandeja_revision(self):
        EntradaRevisionAdmin.objects.create(
            tipo=EntradaRevisionAdmin.TIPO_EXPEDIENTE,
            titulo="Expediente enviado a revisión",
            mensaje="Pendiente revisar expediente.",
            asociacion=self.asociacion,
            estado=EntradaRevisionAdmin.ESTADO_PENDIENTE,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:bandeja_revision"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bandeja de revisión")
        self.assertContains(response, "Expediente enviado a revisión")

    def test_bandeja_revisar_expediente_apunta_a_revision_real(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        EntradaRevisionAdmin.objects.create(
            tipo=EntradaRevisionAdmin.TIPO_EXPEDIENTE,
            titulo="Expediente enviado a revisión",
            mensaje="Pendiente revisar expediente.",
            asociacion=self.asociacion,
            expediente=expediente,
            enlace=reverse("asociaciones:expediente_caimus", args=[self.asociacion.pk]),
            estado=EntradaRevisionAdmin.ESTADO_PENDIENTE,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:bandeja_revision"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("asociaciones:expediente_caimus", args=[self.asociacion.pk]))
        self.assertNotContains(response, reverse("asociaciones:expediente_revision", args=[expediente.pk]))

    def test_admin_puede_abrir_detalle_expediente_caimus_desde_bandeja(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[expediente.asociacion.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Expediente")

    def test_admin_marcar_atendida_por_post_actualiza_estado_y_fecha(self):
        entrada = EntradaRevisionAdmin.objects.create(
            tipo=EntradaRevisionAdmin.TIPO_EXPEDIENTE,
            estado=EntradaRevisionAdmin.ESTADO_PENDIENTE,
            titulo="Expediente pendiente",
            mensaje="Pendiente",
            asociacion=self.asociacion,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.post(reverse("asociaciones:bandeja_marcar_atendida", args=[entrada.pk]))
        self.assertEqual(response.status_code, 302)
        entrada.refresh_from_db()
        self.assertEqual(entrada.estado, EntradaRevisionAdmin.ESTADO_ATENDIDA)
        self.assertIsNotNone(entrada.atendida_en)

    def test_usuario_asociacion_no_puede_marcar_atendida(self):
        entrada = EntradaRevisionAdmin.objects.create(
            tipo=EntradaRevisionAdmin.TIPO_INFORME,
            estado=EntradaRevisionAdmin.ESTADO_PENDIENTE,
            titulo="Informe pendiente",
            mensaje="Pendiente",
            asociacion=self.asociacion,
        )
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.post(reverse("asociaciones:bandeja_marcar_atendida", args=[entrada.pk]))
        self.assertEqual(response.status_code, 403)

    def test_marcar_atendida_disminuye_pendientes_y_no_se_recrea(self):
        expediente = ExpedienteCAIMUS.objects.create(
            asociacion=self.asociacion,
            creado_por=self.admin_user,
            estado=ExpedienteCAIMUS.ESTADO_EN_REVISION,
        )
        entrada = EntradaRevisionAdmin.objects.create(
            tipo=EntradaRevisionAdmin.TIPO_EXPEDIENTE,
            estado=EntradaRevisionAdmin.ESTADO_PENDIENTE,
            titulo="Expediente pendiente",
            mensaje="Pendiente",
            asociacion=self.asociacion,
            expediente=expediente,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.post(reverse("asociaciones:bandeja_marcar_atendida", args=[entrada.pk]))
        self.assertEqual(response.status_code, 302)
        response = client.get(reverse("asociaciones:bandeja_revision"), {"estado": "pendiente"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Expediente pendiente")
        self.assertContains(response, "0 pendientes")

    def test_usuario_asociacion_no_ve_bandeja_revision(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:bandeja_revision"))
        self.assertEqual(response.status_code, 403)

    def test_alerta_admin_revisar_marca_leida_y_redirige(self):
        alerta = NotificacionAdmin.objects.create(
            titulo="Expediente enviado a revisión",
            mensaje="Pendiente revisar expediente.",
            asociacion=self.asociacion,
            enlace=reverse("asociaciones:expediente_caimus", args=[self.asociacion.pk]),
            leida=False,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:alerta_admin_revisar", args=[alerta.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("asociaciones:expediente_caimus", args=[self.asociacion.pk]))
        alerta.refresh_from_db()
        self.assertTrue(alerta.leida)

    def test_upload_narrativo_no_cambia_a_en_revision(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=6,
            estado=InformeMensual.ESTADO_BORRADOR,
            creado_por=self.user,
        )
        client = Client()
        client.login(username="user1", password="pass123")
        archivo = SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf")
        response = client.post(
            reverse("asociaciones:informe_upload_narrativo", args=[self.asociacion.pk, informe.mes]),
            {"pdf": archivo},
        )
        self.assertEqual(response.status_code, 302)
        informe.refresh_from_db()
        self.assertEqual(informe.estado, InformeMensual.ESTADO_BORRADOR)

    def test_boton_enviar_revision_visible_para_usuario_asociacion(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:informes_mensuales", args=[self.asociacion.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enviar a revisión")

    def test_upload_presupuestario_no_cambia_a_en_revision(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=7,
            estado=InformeMensual.ESTADO_RECHAZADO,
            creado_por=self.user,
        )
        client = Client()
        client.login(username="user1", password="pass123")
        archivo = SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf")
        response = client.post(
            reverse("asociaciones:informe_upload_presupuestario", args=[self.asociacion.pk, informe.mes]),
            {"pdf": archivo},
        )
        self.assertEqual(response.status_code, 302)
        informe.refresh_from_db()
        self.assertEqual(informe.estado, InformeMensual.ESTADO_BORRADOR)

    def test_guardar_observaciones_no_cambia_a_en_revision(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=11,
            estado=InformeMensual.ESTADO_BORRADOR,
            creado_por=self.user,
        )
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.post(
            reverse("asociaciones:informe_observacion", args=[self.asociacion.pk, informe.mes]),
            {"observaciones": "Revisión previa"},
        )
        self.assertEqual(response.status_code, 302)
        informe.refresh_from_db()
        self.assertEqual(informe.estado, InformeMensual.ESTADO_BORRADOR)

    def test_informe_aprobado_marca_entrada_bandeja_como_atendida(self):
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=12,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            archivo_presupuestario=SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_EN_REVISION,
            creado_por=self.user,
        )
        entrada = EntradaRevisionAdmin.objects.create(
            tipo=EntradaRevisionAdmin.TIPO_INFORME,
            estado=EntradaRevisionAdmin.ESTADO_PENDIENTE,
            titulo="Informe pendiente",
            mensaje="Pendiente",
            asociacion=self.asociacion,
            informe=informe,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.post(
            reverse("asociaciones:informe_estado", args=[self.asociacion.pk, informe.mes]),
            {"estado": InformeMensual.ESTADO_APROBADO, "observacion_admin": ""},
        )
        self.assertEqual(response.status_code, 302)
        entrada.refresh_from_db()
        self.assertEqual(entrada.estado, EntradaRevisionAdmin.ESTADO_ATENDIDA)

    def test_expediente_aprobado_marca_entrada_bandeja_como_atendida(self):
        expediente = ExpedienteCAIMUS.objects.create(
            asociacion=self.asociacion,
            creado_por=self.user,
            estado=ExpedienteCAIMUS.ESTADO_EN_REVISION,
        )
        entrada = EntradaRevisionAdmin.objects.create(
            tipo=EntradaRevisionAdmin.TIPO_EXPEDIENTE,
            estado=EntradaRevisionAdmin.ESTADO_PENDIENTE,
            titulo="Expediente pendiente",
            mensaje="Pendiente",
            asociacion=self.asociacion,
            expediente=expediente,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.post(
            reverse("asociaciones:expediente_revision", args=[expediente.pk]),
            {"estado": ExpedienteCAIMUS.ESTADO_APROBADO, "observacion_admin": ""},
        )
        self.assertEqual(response.status_code, 302)
        entrada.refresh_from_db()
        self.assertEqual(entrada.estado, EntradaRevisionAdmin.ESTADO_ATENDIDA)

    def test_dashboard_admin_filtra_por_anio(self):
        Asociacion.objects.create(anio=self.anio_otro, nombre="Asociacion 2027", codigo="A27")
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:dashboard"), {"anio": 2026})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.asociacion.nombre)
        self.assertNotContains(response, "Asociacion 2027")

    def test_dashboard_admin_select_anios_muestra_solo_activos(self):
        anio_inactivo = Anio.objects.create(anio=2025, activo=False)
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.anio.anio))
        self.assertNotContains(response, str(anio_inactivo.anio))

    def test_dashboard_asociacion_filtra_por_anio_sin_exponer_otros(self):
        asociacion_2027 = Asociacion.objects.create(anio=self.anio_otro, nombre="Asociacion U 2027", codigo="U27")
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        AsociacionUsuario.objects.create(asociacion=asociacion_2027, usuario=self.user, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:dashboard"), {"anio": 2026})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.asociacion.nombre)
        self.assertNotContains(response, "Asociacion U 2027")

    def test_dashboard_asociacion_permite_seleccionar_asociacion_por_get(self):
        asociacion_extra = Asociacion.objects.create(anio=self.anio, nombre="Asociacion Extra", codigo="AEX")
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        AsociacionUsuario.objects.create(asociacion=asociacion_extra, usuario=self.user, rol_en_asociacion="Miembro")
        InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=1,
            estado=InformeMensual.ESTADO_APROBADO,
            creado_por=self.user,
        )
        InformeMensual.objects.create(
            asociacion=asociacion_extra,
            mes=2,
            estado=InformeMensual.ESTADO_BORRADOR,
            creado_por=self.user,
        )
        NotificacionAsociacion.objects.create(asociacion=self.asociacion, titulo="Notif A", mensaje="A")
        NotificacionAsociacion.objects.create(asociacion=asociacion_extra, titulo="Notif B", mensaje="B")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(
            reverse("asociaciones:dashboard"),
            {"anio": self.anio.anio, "asociacion": asociacion_extra.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ver información de la asociación")
        self.assertContains(response, "Asociacion Extra")
        self.assertContains(response, "Notif B")
        self.assertNotContains(response, "Notif A")

    def test_dashboard_asociacion_rechaza_seleccion_de_asociacion_ajena(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(
            reverse("asociaciones:dashboard"),
            {"anio": self.anio.anio, "asociacion": self.asociacion_otra.pk},
        )
        self.assertEqual(response.status_code, 403)

    def test_usuario_otra_asociacion_no_ve_observaciones_ajenas(self):
        expediente = ExpedienteCAIMUS.objects.create(
            asociacion=self.asociacion,
            creado_por=self.admin_user,
            observacion_admin="Observación privada",
        )
        user_otro = User.objects.create_user(username="otro_obs", password="pass123")
        user_otro.groups.add(self.asociacion_group)
        AsociacionUsuario.objects.create(asociacion=self.asociacion_otra, usuario=user_otro, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="otro_obs", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[expediente.asociacion.pk]))
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
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=1,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            archivo_presupuestario=SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_EN_REVISION,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.post(
            reverse("asociaciones:informe_estado", args=[self.asociacion.pk, informe.mes]),
            {"estado": InformeMensual.ESTADO_APROBADO},
        )
        self.assertEqual(response.status_code, 302)
        informe.refresh_from_db()
        self.assertEqual(informe.estado, InformeMensual.ESTADO_APROBADO)
        self.assertTrue(ResolucionInformeMensual.objects.filter(informe=informe).exists())
        self.assertTrue(
            NotificacionAsociacion.objects.filter(
                asociacion=self.asociacion,
                titulo="Informe mensual aprobado",
            ).exists()
        )

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


    def test_guardar_checklist_anio_sincroniza_expedientes_existentes(self):
        item_anio = ChecklistAnioItem.objects.create(anio=self.anio, numero=1, titulo="Doc 1", activo=True)
        item_activo = ChecklistAnioItem.objects.create(anio=self.anio, numero=2, titulo="Doc 2", activo=True)
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        crear_items_expediente(expediente)
        item_anio.delete()

        client = Client()
        client.login(username="admin", password="pass123")
        payload = {
            "checklist-TOTAL_FORMS": "1",
            "checklist-INITIAL_FORMS": "1",
            "checklist-MIN_NUM_FORMS": "0",
            "checklist-MAX_NUM_FORMS": "1000",
            "checklist-0-id": str(item_activo.pk),
            "checklist-0-numero": "2",
            "checklist-0-titulo": "Doc 2",
            "checklist-0-descripcion": "",
            "checklist-0-activo": "on",
            "checklist-0-DELETE": "",
        }
        response = client.post(reverse("asociaciones:anio_checklist_guardar", args=[self.anio.pk]), payload)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(expediente.items.get(numero=1).activo)

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


    def test_sincronizacion_desactiva_items_eliminados_sin_borrar_datos(self):
        item_anio = ChecklistAnioItem.objects.create(anio=self.anio, numero=1, titulo="Doc 1", activo=True)
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        crear_items_expediente(expediente)
        item = expediente.items.get(numero=1)
        item.observaciones = "Observación histórica"
        item.pdf = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        item.save()

        item_anio.delete()
        crear_items_expediente(expediente)

        item.refresh_from_db()
        self.assertFalse(item.activo)
        self.assertTrue(bool(item.pdf))
        self.assertEqual(item.observaciones, "Observación histórica")

    def test_sincronizacion_agrega_nuevo_item_del_checklist(self):
        ChecklistAnioItem.objects.create(anio=self.anio, numero=1, titulo="Doc 1", activo=True)
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        crear_items_expediente(expediente)

        ChecklistAnioItem.objects.create(anio=self.anio, numero=2, titulo="Doc 2", activo=True)
        crear_items_expediente(expediente)

        self.assertTrue(expediente.items.filter(numero=2, activo=True, titulo="Doc 2").exists())

    def test_expediente_renderiza_checklist_en_accordion(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        ChecklistAnioItem.objects.create(anio=self.anio, numero=1, titulo="Doc 1", activo=True)

        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:expediente_caimus", args=[self.asociacion.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="accordionChecklist"')
        self.assertContains(response, "accordion-item")
        self.assertContains(response, "toggle-icon")

    def test_informes_renderiza_meses_en_accordion(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        InformeMensual.objects.create(asociacion=self.asociacion, mes=1)

        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:informes_mensuales", args=[self.asociacion.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="accordionInformes"')
        self.assertContains(response, "accordion-item")
        self.assertContains(response, "accordion-meta-item")

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
            reverse("asociaciones:informe_upload_narrativo", args=[self.asociacion.pk, informe.mes]),
            {"pdf": archivo},
        )
        informe.refresh_from_db()
        self.assertTrue(informe.archivo_narrativo)
        self.assertEqual(informe.estado, InformeMensual.ESTADO_BORRADOR)
        self.assertEqual(informe.observaciones_usuario, "Obs")

    def test_usuario_asociacion_puede_subir_presupuestario_sin_enviar_a_revision(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=2,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
        )
        client = Client()
        client.login(username="user1", password="pass123")
        archivo = SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf")
        response = client.post(
            reverse("asociaciones:informe_upload_presupuestario", args=[self.asociacion.pk, informe.mes]),
            {"pdf": archivo},
        )
        self.assertEqual(response.status_code, 302)
        informe.refresh_from_db()
        self.assertTrue(informe.archivo_presupuestario)
        self.assertEqual(informe.estado, InformeMensual.ESTADO_BORRADOR)
        self.assertFalse(
            EntradaRevisionAdmin.objects.filter(
                informe=informe,
                estado=EntradaRevisionAdmin.ESTADO_PENDIENTE,
            ).exists()
        )

    def test_dashboard_admin_muestra_informes_en_revision_aun_si_falta_entrada(self):
        InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=4,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            archivo_presupuestario=SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_EN_REVISION,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:dashboard"), {"anio": self.anio.anio})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alertas nuevas")
        self.assertTrue(
            EntradaRevisionAdmin.objects.filter(
                informe__asociacion=self.asociacion,
                informe__mes=4,
                estado=EntradaRevisionAdmin.ESTADO_PENDIENTE,
            ).exists()
        )

    def test_no_se_puede_aprobar_informe_si_falta_un_archivo(self):
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=3,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_EN_REVISION,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.post(
            reverse("asociaciones:informe_estado", args=[self.asociacion.pk, informe.mes]),
            {"estado": InformeMensual.ESTADO_APROBADO},
        )
        self.assertEqual(response.status_code, 302)
        informe.refresh_from_db()
        self.assertNotEqual(informe.estado, InformeMensual.ESTADO_APROBADO)
        self.assertFalse(ResolucionInformeMensual.objects.filter(informe=informe).exists())

    def test_admin_aprueba_expediente_crea_notificacion(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        client = Client()
        client.login(username="admin", password="pass123")
        client.post(
            reverse("asociaciones:expediente_revision", args=[expediente.pk]),
            {"estado": ExpedienteCAIMUS.ESTADO_APROBADO, "observacion_admin": ""},
        )
        self.assertTrue(
            NotificacionAsociacion.objects.filter(
                asociacion=self.asociacion,
                titulo="Expediente aprobado",
            ).exists()
        )

    def test_usuario_asociacion_solo_ve_notificaciones_de_su_asociacion(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        NotificacionAsociacion.objects.create(asociacion=self.asociacion, titulo="Notif 1", mensaje="Visible")
        NotificacionAsociacion.objects.create(asociacion=self.asociacion_otra, titulo="Notif 2", mensaje="No visible")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:mis_asociaciones"))
        self.assertContains(response, "Notif 1")
        self.assertNotContains(response, "Notif 2")

    def test_usuario_de_otra_asociacion_no_puede_marcar_alertas_ajenas(self):
        user_otro = User.objects.create_user(username="otro", password="pass123")
        user_otro.groups.add(self.asociacion_group)
        AsociacionUsuario.objects.create(asociacion=self.asociacion_otra, usuario=user_otro, rol_en_asociacion="Miembro")
        notificacion = NotificacionAsociacion.objects.create(asociacion=self.asociacion, titulo="Notif", mensaje="Msg")
        client = Client()
        client.login(username="otro", password="pass123")
        response = client.post(reverse("asociaciones:notificaciones_marcar_leidas", args=[self.asociacion.pk]))
        self.assertEqual(response.status_code, 403)
        notificacion.refresh_from_db()
        self.assertFalse(notificacion.leida)

    def test_marcar_alertas_como_leidas_funciona(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        notificacion = NotificacionAsociacion.objects.create(asociacion=self.asociacion, titulo="Notif", mensaje="Msg")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.post(reverse("asociaciones:notificaciones_marcar_leidas", args=[self.asociacion.pk]))
        self.assertEqual(response.status_code, 302)
        notificacion.refresh_from_db()
        self.assertTrue(notificacion.leida)

    def test_usuario_asociacion_puede_descargar_constancia_informe_aprobado(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=4,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            archivo_presupuestario=SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_APROBADO,
        )
        ResolucionInformeMensual.objects.create(
            informe=informe,
            correlativo="UPCV-INF-2026-04-0001",
            fecha_emision=date.today(),
            generado_por=self.admin_user,
        )
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:informe_resolucion_pdf", args=[self.asociacion.pk, informe.mes]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_usuario_asociacion_recibe_403_constancia_si_no_aprobado(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=6,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            archivo_presupuestario=SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_EN_REVISION,
        )
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:informe_resolucion_pdf", args=[self.asociacion.pk, informe.mes]))
        self.assertEqual(response.status_code, 403)

    def test_usuario_otra_asociacion_recibe_403_en_constancia(self):
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=5,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            archivo_presupuestario=SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_APROBADO,
        )
        ResolucionInformeMensual.objects.create(
            informe=informe,
            correlativo="UPCV-INF-2026-05-0001",
            fecha_emision=date.today(),
            generado_por=self.admin_user,
        )
        user_otro = User.objects.create_user(username="otro", password="pass123")
        user_otro.groups.add(self.asociacion_group)
        AsociacionUsuario.objects.create(asociacion=self.asociacion_otra, usuario=user_otro, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="otro", password="pass123")
        response = client.get(reverse("asociaciones:informe_resolucion_pdf", args=[self.asociacion.pk, informe.mes]))
        self.assertEqual(response.status_code, 403)

    def test_admin_puede_descargar_constancia(self):
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=7,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            archivo_presupuestario=SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_APROBADO,
        )
        client = Client()
        client.login(username="admin", password="pass123")
        response = client.get(reverse("asociaciones:informe_resolucion_pdf", args=[self.asociacion.pk, informe.mes]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_descarga_constancia_genera_resolucion_si_no_existe(self):
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        informe = InformeMensual.objects.create(
            asociacion=self.asociacion,
            mes=8,
            archivo_narrativo=SimpleUploadedFile("narrativo.pdf", b"%PDF-1.4 nar", content_type="application/pdf"),
            archivo_presupuestario=SimpleUploadedFile("presupuestario.pdf", b"%PDF-1.4 pre", content_type="application/pdf"),
            estado=InformeMensual.ESTADO_APROBADO,
        )
        self.assertFalse(ResolucionInformeMensual.objects.filter(informe=informe).exists())
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:informe_resolucion_pdf", args=[self.asociacion.pk, informe.mes]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(ResolucionInformeMensual.objects.filter(informe=informe).exists())

    

    def test_asociacion_no_puede_descargar_informe_trazabilidad(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        AsociacionUsuario.objects.create(asociacion=self.asociacion, usuario=self.user, rol_en_asociacion="Miembro")
        client = Client()
        client.login(username="user1", password="pass123")
        response = client.get(reverse("asociaciones:informe_trazabilidad_expediente_pdf", args=[expediente.pk]))
        self.assertEqual(response.status_code, 403)

    def test_informatica_puede_descargar_informe_trazabilidad(self):
        expediente = ExpedienteCAIMUS.objects.create(asociacion=self.asociacion, creado_por=self.admin_user)
        client = Client()
        client.login(username="informatica", password="pass123")
        response = client.get(reverse("asociaciones:informe_trazabilidad_expediente_pdf", args=[expediente.pk]))
        self.assertEqual(response.status_code, 200)

    def test_informe_trazabilidad_sin_numero_muestra_sin_asignar(self):
        expediente = ExpedienteCAIMUS.objects.create(
            asociacion=self.asociacion,
            creado_por=self.admin_user,
            estado=ExpedienteCAIMUS.ESTADO_BORRADOR,
        )
        client = Client()
        client.login(username="informatica", password="pass123")

        url = reverse("asociaciones:informe_trazabilidad_expediente_pdf", args=[expediente.pk])
        for _ in range(2):
            response = client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "application/pdf")
            self.assertIn(
                f"Informe_Trazabilidad_Sin_Asignar_Expediente_{expediente.pk}.pdf",
                response["Content-Disposition"],
            )
            texto_pdf = "".join(page.extract_text() or "" for page in PdfReader(BytesIO(response.content)).pages)
            self.assertIn("Sin asignar", texto_pdf)
            self.assertIn("Borrador", texto_pdf)

        expediente.refresh_from_db()
        self.assertEqual(expediente.estado, ExpedienteCAIMUS.ESTADO_BORRADOR)
        self.assertFalse(ResolucionExpediente.objects.filter(expediente=expediente).exists())

        expediente.estado = ExpedienteCAIMUS.ESTADO_EN_REVISION
        expediente.save(update_fields=["estado"])
        response = client.get(url)
        texto_pdf = "".join(page.extract_text() or "" for page in PdfReader(BytesIO(response.content)).pages)
        self.assertIn("Sin asignar", texto_pdf)
        self.assertIn("En revisión", texto_pdf)
        self.assertFalse(ResolucionExpediente.objects.filter(expediente=expediente).exists())

    def test_informe_trazabilidad_aprobado_muestra_correlativo_oficial(self):
        expediente = self._crear_expediente_aprobado_completo()
        client = Client()
        client.login(username="informatica", password="pass123")

        response = client.get(
            reverse("asociaciones:informe_trazabilidad_expediente_pdf", args=[expediente.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("Informe_Trazabilidad_RES-2026-001.pdf", response["Content-Disposition"])
        texto_pdf = "".join(page.extract_text() or "" for page in PdfReader(BytesIO(response.content)).pages)
        self.assertIn("RES-2026-001", texto_pdf)
        self.assertIn("Aprobado", texto_pdf)
