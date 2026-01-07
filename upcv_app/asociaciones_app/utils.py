from __future__ import annotations

from typing import Optional

from .models import Asociacion, AsociacionUsuario


def is_admin(user) -> bool:
    if not user.is_authenticated:
        return False
    return user.groups.filter(name="Administrador").exists() or user.is_superuser


def usuario_puede_ver_asociacion(user, asociacion: Asociacion) -> bool:
    if is_admin(user):
        return True
    return AsociacionUsuario.objects.filter(usuario=user, asociacion=asociacion, activo=True).exists()


def obtener_asignacion_activa(user, asociacion: Asociacion) -> Optional[AsociacionUsuario]:
    return AsociacionUsuario.objects.filter(usuario=user, asociacion=asociacion, activo=True).first()
