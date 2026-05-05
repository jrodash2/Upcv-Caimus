from .permissions import is_superadmin


def permisos_globales(request):
    user = request.user
    return {
        "puede_ver_configuracion": is_superadmin(user),
        "es_superadmin": is_superadmin(user),
    }
