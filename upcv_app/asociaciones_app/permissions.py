from __future__ import annotations

from django.db.models import QuerySet

from .models import Asociacion, AsociacionUsuario, ExpedienteCAIMUS


def is_admin(user) -> bool:
    if not user.is_authenticated:
        return False
    return user.groups.filter(name="Administrador").exists() or user.is_superuser


def is_asociacion(user) -> bool:
    if not user.is_authenticated:
        return False
    return user.groups.filter(name="Asociacion").exists()


def get_asociaciones_usuario(user) -> QuerySet[Asociacion]:
    if not user.is_authenticated:
        return Asociacion.objects.none()
    return Asociacion.objects.filter(
        activo=True,
        usuarios__usuario=user,
        usuarios__activo=True,
    ).distinct()


def user_has_asociacion_access(user, asociacion: Asociacion) -> bool:
    if is_admin(user):
        return True
    if not is_asociacion(user):
        return False
    return AsociacionUsuario.objects.filter(
        usuario=user,
        asociacion=asociacion,
        activo=True,
        asociacion__activo=True,
    ).exists()


def user_has_expediente_access(user, expediente: ExpedienteCAIMUS) -> bool:
    return user_has_asociacion_access(user, expediente.asociacion)


def user_can_download_resolucion(user, expediente: ExpedienteCAIMUS) -> bool:
    if expediente.estado != ExpedienteCAIMUS.ESTADO_APROBADO:
        return False
    if is_admin(user):
        return True
    if not is_asociacion(user):
        return False
    return AsociacionUsuario.objects.filter(
        usuario=user,
        asociacion=expediente.asociacion,
        activo=True,
        asociacion__activo=True,
    ).exists()
