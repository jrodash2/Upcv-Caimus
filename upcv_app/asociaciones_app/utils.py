from __future__ import annotations

from typing import Optional

from django.db.models import Q
from django.urls import reverse

from .models import Asociacion, AsociacionUsuario
from .models import EntradaRevisionAdmin, ExpedienteCAIMUS, InformeMensual, NotificacionAdmin, crear_entrada_revision_admin


def is_admin(user) -> bool:
    return (
        user.is_authenticated
        and (
            user.groups.filter(name__iexact="Administrador").exists()
            or user.groups.filter(name__iexact="Informatica").exists()
        )
    )


def usuario_puede_ver_asociacion(user, asociacion: Asociacion) -> bool:
    if is_admin(user):
        return True
    return AsociacionUsuario.objects.filter(usuario=user, asociacion=asociacion, activo=True).exists()


def obtener_asignacion_activa(user, asociacion: Asociacion) -> Optional[AsociacionUsuario]:
    return AsociacionUsuario.objects.filter(usuario=user, asociacion=asociacion, activo=True).first()


def _resolver_anio_id(anio) -> Optional[int]:
    if anio is None:
        return None
    if hasattr(anio, "pk"):
        return anio.pk
    try:
        return int(anio)
    except (TypeError, ValueError):
        return None


def sincronizar_entradas_revision_admin(anio=None) -> None:
    anio_id = _resolver_anio_id(anio)
    informes_en_revision = InformeMensual.objects.filter(estado=InformeMensual.ESTADO_EN_REVISION).select_related("asociacion", "asociacion__anio")
    expedientes_en_revision = ExpedienteCAIMUS.objects.filter(estado=ExpedienteCAIMUS.ESTADO_EN_REVISION).select_related("asociacion", "asociacion__anio")
    if anio_id:
        informes_en_revision = informes_en_revision.filter(asociacion__anio_id=anio_id)
        expedientes_en_revision = expedientes_en_revision.filter(asociacion__anio_id=anio_id)

    existentes_informes = set(
        EntradaRevisionAdmin.objects.filter(
            informe__in=informes_en_revision,
        ).values_list("informe_id", flat=True)
    )
    for informe in informes_en_revision.exclude(id__in=existentes_informes):
        crear_entrada_revision_admin(
            tipo=EntradaRevisionAdmin.TIPO_INFORME,
            titulo="Informe enviado a revisión",
            mensaje=f"Informe {informe.get_mes_display()} de {informe.asociacion.nombre} requiere revisión.",
            enlace=f"{reverse('asociaciones:informes_mensuales', args=[informe.asociacion_id])}#informe-mes-{informe.mes}",
            asociacion=informe.asociacion,
            informe=informe,
        )

    existentes_expedientes = set(
        EntradaRevisionAdmin.objects.filter(
            expediente__in=expedientes_en_revision,
        ).values_list("expediente_id", flat=True)
    )
    for expediente in expedientes_en_revision.exclude(id__in=existentes_expedientes):
        crear_entrada_revision_admin(
            tipo=EntradaRevisionAdmin.TIPO_EXPEDIENTE,
            titulo="Expediente enviado a revisión",
            mensaje=f"Expediente de {expediente.asociacion.nombre} requiere revisión.",
            enlace=reverse("asociaciones:expediente_caimus", args=[expediente.asociacion_id]),
            asociacion=expediente.asociacion,
            expediente=expediente,
        )


def obtener_entradas_bandeja_admin(anio=None, estado=None, tipo=None):
    sincronizar_entradas_revision_admin(anio=anio)
    anio_id = _resolver_anio_id(anio)
    qs = EntradaRevisionAdmin.objects.select_related("asociacion", "asociacion__anio", "expediente", "informe")
    if anio_id:
        qs = qs.filter(
            Q(asociacion__anio_id=anio_id)
            | Q(expediente__asociacion__anio_id=anio_id)
            | Q(informe__asociacion__anio_id=anio_id)
        )
    if estado:
        qs = qs.filter(estado=estado)
    if tipo:
        qs = qs.filter(tipo=tipo)
    return qs.order_by("-creada_en")


def obtener_alertas_admin_no_leidas(anio=None):
    anio_id = _resolver_anio_id(anio)
    qs = NotificacionAdmin.objects.select_related("asociacion", "informe").filter(leida=False)
    if anio_id:
        qs = qs.filter(
            Q(asociacion__anio_id=anio_id)
            | Q(informe__asociacion__anio_id=anio_id)
            | Q(asociacion__isnull=True, informe__isnull=True)
        )
    return qs.order_by("-creada_en")


def resumen_dashboard_admin(anio=None):
    entradas_pendientes = obtener_entradas_bandeja_admin(anio=anio, estado=EntradaRevisionAdmin.ESTADO_PENDIENTE)
    alertas_no_leidas = obtener_alertas_admin_no_leidas(anio=anio)
    return {
        "total_bandeja_pendiente": entradas_pendientes.count(),
        "entradas_bandeja_recientes": entradas_pendientes[:5],
        "total_alertas_no_leidas": alertas_no_leidas.count(),
        "alertas_no_leidas_recientes": alertas_no_leidas[:8],
    }
