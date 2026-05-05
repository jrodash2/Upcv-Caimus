
from functools import wraps
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from asociaciones_app.permissions import is_informatica

def reservar_lineas(cantidad, form1h_instance):
    contador_global, _ = ContadorDetalleFactura.objects.get_or_create(id=1)
    lineas_reservadas = []

    for _ in range(cantidad):
        if LineaLibre.objects.exists():
            libre = LineaLibre.objects.first()
            numero_linea = libre.id_linea
            libre.delete()
        else:
            numero_linea = contador_global.contador
            contador_global.contador += 1

        # Verifica que no haya duplicado antes de crear
        if not LineaReservada.objects.filter(numero_linea=numero_linea).exists():
            linea_reservada = LineaReservada.objects.create(
                numero_linea=numero_linea,
                disponible=True,
                form1h=form1h_instance
            )
            lineas_reservadas.append(linea_reservada)

    contador_global.save()
    return lineas_reservadas


def informatica_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not is_informatica(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped


def grupo_requerido(*nombres_grupos):
    def decorador(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and any(
                request.user.groups.filter(name__iexact=nombre_grupo).exists()
                for nombre_grupo in nombres_grupos
            ):
                return view_func(request, *args, **kwargs)
            # Redirigir a la vista de acceso denegado
            return redirect(reverse('almacen:acceso_denegado'))
        return _wrapped_view
    return decorador


from django.db.models import Sum

def obtener_articulos_asignados(departamento):
    asignaciones = AsignacionDetalleFactura.objects.filter(destino=departamento)
    return asignaciones.values('articulo').annotate(
        total_asignado=Sum('cantidad_asignada')
    )
