from django.contrib import admin

from .models import (
    Anio,
    Asociacion,
    AsociacionUsuario,
    ExpedienteCAIMUS,
    ItemChecklistCAIMUS,
    ExpedienteEstadoHistorial,
    ResolucionExpediente,
)


admin.site.register(Anio)
admin.site.register(Asociacion)
admin.site.register(AsociacionUsuario)
admin.site.register(ExpedienteCAIMUS)
admin.site.register(ItemChecklistCAIMUS)
admin.site.register(ExpedienteEstadoHistorial)
admin.site.register(ResolucionExpediente)
