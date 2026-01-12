from django.urls import path

from . import views

app_name = "asociaciones"

urlpatterns = [
    path("anios/", views.anio_list, name="anios_list"),
    path("anios/nuevo/", views.anio_create, name="anio_create"),
    path("anios/<int:pk>/editar/", views.anio_edit, name="anio_edit"),
    path("<int:anio_id>/lista/", views.asociacion_list, name="asociacion_list"),
    path("<int:anio_id>/nuevo/", views.asociacion_create, name="asociacion_create"),
    path("<int:pk>/editar/", views.asociacion_edit, name="asociacion_edit"),
    path("<int:pk>/usuarios/", views.asociacion_usuarios, name="asociacion_usuarios"),
    path("mis-asociaciones/", views.mis_asociaciones, name="mis_asociaciones"),
    path("<int:pk>/caimus/", views.expediente_caimus, name="expediente_caimus"),
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
        "<int:asociacion_id>/informes/<int:mes>/observacion/",
        views.informe_observacion,
        name="informe_observacion",
    ),
    path(
        "<int:asociacion_id>/informes/<int:mes>/estado/",
        views.informe_estado,
        name="informe_estado",
    ),
    path("bandeja-revision/", views.bandeja_revision, name="bandeja_revision"),
    path("asignaciones/", views.asignaciones_list, name="asignaciones_list"),
]
