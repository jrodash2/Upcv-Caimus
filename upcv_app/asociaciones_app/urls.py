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
    path("expedientes/<int:pk>/revision/", views.expediente_revision, name="expediente_revision"),
    path("expedientes/<int:pk>/resolucion/pdf/", views.resolucion_pdf, name="resolucion_pdf"),
    path("bandeja-revision/", views.bandeja_revision, name="bandeja_revision"),
    path("asignaciones/", views.asignaciones_list, name="asignaciones_list"),
]
