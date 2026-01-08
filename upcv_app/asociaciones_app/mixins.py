from __future__ import annotations

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .models import Asociacion, ExpedienteCAIMUS
from .permissions import is_admin, is_asociacion, user_has_asociacion_access, user_has_expediente_access


class AdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class AsociacionRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not (is_admin(request.user) or is_asociacion(request.user)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class AsociacionObjectAccessMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if isinstance(obj, Asociacion):
            permitido = user_has_asociacion_access(request.user, obj)
        elif isinstance(obj, ExpedienteCAIMUS):
            permitido = user_has_expediente_access(request.user, obj)
        else:
            permitido = False
        if not permitido:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped


def asociacion_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not (is_admin(request.user) or is_asociacion(request.user)):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped
