from django.urls import path

from . import views

app_name = "asociaciones"

urlpatterns = [
    path("", views.asociaciones_inicio, name="inicio"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("anios/", views.anio_list, name="anios_list"),
    path("anios/nuevo/", views.anio_create, name="anio_create"),
    path("anios/<int:pk>/editar/", views.anio_edit, name="anio_edit"),
    path("anios/<int:pk>/checklist/", views.anio_checklist, name="anio_checklist"),
    path("anios/<int:pk>/checklist/guardar/", views.anio_checklist_guardar, name="anio_checklist_guardar"),
    path("<int:anio_id>/lista/", views.asociacion_list, name="asociacion_list"),
    path("<int:anio_id>/nuevo/", views.asociacion_create, name="asociacion_create"),
    path("<int:pk>/editar/", views.asociacion_edit, name="asociacion_edit"),
    path("<int:pk>/usuarios/", views.asociacion_usuarios, name="asociacion_usuarios"),
    path("mis-asociaciones/", views.mis_asociaciones, name="mis_asociaciones"),
    path(
        "<int:asociacion_id>/notificaciones/marcar-leidas/",
        views.notificaciones_marcar_leidas,
        name="notificaciones_marcar_leidas",
    ),
    path("<int:pk>/caimus/", views.expediente_caimus, name="expediente_caimus"),
    path("<int:pk>/caimus/enviar-revision/", views.expediente_enviar_revision, name="expediente_enviar_revision"),
    path("<int:pk>/caimus/sincronizar-checklist/", views.expediente_sync_checklist, name="expediente_sync_checklist"),
    path("<int:pk>/informes/", views.informes_mensuales, name="informes_mensuales"),
    path("expedientes/<int:pk>/revision/", views.expediente_revision, name="expediente_revision"),
    path("expedientes/<int:pk>/resolucion/pdf/", views.resolucion_pdf, name="resolucion_pdf"),
    path(
        "expedientes/<int:expediente_id>/items/<int:item_id>/upload/",
        views.item_upload,
        name="item_upload",
    ),
    path(
        "expedientes/<int:expediente_id>/items/<int:item_id>/observacion/",
        views.item_observacion,
        name="item_observacion",
    ),
    path(
        "<int:asociacion_id>/informes/<int:mes>/upload/",
        views.informe_upload,
        name="informe_upload",
    ),
    path(
        "<int:asociacion_id>/informes/<int:mes>/upload/narrativo/",
        views.informe_upload_narrativo,
        name="informe_upload_narrativo",
    ),
    path(
        "<int:asociacion_id>/informes/<int:mes>/upload/presupuestario/",
        views.informe_upload_presupuestario,
        name="informe_upload_presupuestario",
    ),
    path(
        "<int:asociacion_id>/informes/<int:mes>/observacion/",
        views.informe_observacion,
        name="informe_observacion",
    ),
    path(
        "<int:asociacion_id>/informes/<int:mes>/enviar-revision/",
        views.informe_enviar_revision,
        name="informe_enviar_revision",
    ),
    path(
        "<int:asociacion_id>/informes/<int:mes>/estado/",
        views.informe_estado,
        name="informe_estado",
    ),
    path(
        "<int:asociacion_id>/informes/<int:mes>/resolucion/pdf/",
        views.informe_resolucion_pdf,
        name="informe_resolucion_pdf",
    ),
    path("bandeja-revision/", views.bandeja_revision, name="bandeja_revision"),
    path("asignaciones/", views.asignaciones_list, name="asignaciones_list"),
]
