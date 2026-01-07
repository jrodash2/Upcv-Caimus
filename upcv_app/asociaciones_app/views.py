from __future__ import annotations

from typing import Dict, List

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from weasyprint import HTML

from .forms import (
    AnioForm,
    AsociacionForm,
    AsociacionUsuarioForm,
    ExpedienteCAIMUSForm,
    ItemChecklistFormSet,
    RevisionExpedienteForm,
)
from .models import (
    Anio,
    Asociacion,
    AsociacionUsuario,
    ExpedienteCAIMUS,
    ExpedienteEstadoHistorial,
    ResolucionExpediente,
    crear_items_expediente,
    generar_correlativo,
)
from .utils import is_admin, obtener_asignacion_activa, usuario_puede_ver_asociacion


def admin_required(view_func):
    return user_passes_test(is_admin)(view_func)


@login_required
@admin_required
def anio_list(request):
    anios = Anio.objects.all()
    return render(request, "asociaciones_app/anio_list.html", {"anios": anios})


@login_required
@admin_required
def anio_create(request):
    if request.method == "POST":
        form = AnioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Año creado correctamente.")
            return redirect("asociaciones:anios_list")
    else:
        form = AnioForm()
    return render(request, "asociaciones_app/anio_form.html", {"form": form, "titulo": "Nuevo año"})


@login_required
@admin_required
def anio_edit(request, pk):
    anio = get_object_or_404(Anio, pk=pk)
    if request.method == "POST":
        form = AnioForm(request.POST, instance=anio)
        if form.is_valid():
            form.save()
            messages.success(request, "Año actualizado correctamente.")
            return redirect("asociaciones:anios_list")
    else:
        form = AnioForm(instance=anio)
    return render(request, "asociaciones_app/anio_form.html", {"form": form, "titulo": "Editar año"})


@login_required
@admin_required
def asociacion_list(request, anio_id):
    anio = get_object_or_404(Anio, pk=anio_id)
    asociaciones = anio.asociaciones.all()
    return render(
        request,
        "asociaciones_app/asociacion_list.html",
        {"anio": anio, "asociaciones": asociaciones},
    )


@login_required
@admin_required
def asociacion_create(request, anio_id):
    anio = get_object_or_404(Anio, pk=anio_id)
    if request.method == "POST":
        form = AsociacionForm(request.POST)
        if form.is_valid():
            asociacion = form.save()
            messages.success(request, "Asociación creada correctamente.")
            return redirect("asociaciones:asociacion_list", anio_id=asociacion.anio_id)
    else:
        form = AsociacionForm(initial={"anio": anio})
    return render(
        request,
        "asociaciones_app/asociacion_form.html",
        {"form": form, "anio": anio, "titulo": "Nueva asociación"},
    )


@login_required
@admin_required
def asociacion_edit(request, pk):
    asociacion = get_object_or_404(Asociacion, pk=pk)
    if request.method == "POST":
        form = AsociacionForm(request.POST, instance=asociacion)
        if form.is_valid():
            form.save()
            messages.success(request, "Asociación actualizada correctamente.")
            return redirect("asociaciones:asociacion_list", anio_id=asociacion.anio_id)
    else:
        form = AsociacionForm(instance=asociacion)
    return render(
        request,
        "asociaciones_app/asociacion_form.html",
        {"form": form, "anio": asociacion.anio, "titulo": "Editar asociación"},
    )


@login_required
@admin_required
def asociacion_usuarios(request, pk):
    asociacion = get_object_or_404(Asociacion, pk=pk)
    if request.method == "POST":
        form = AsociacionUsuarioForm(request.POST)
        if form.is_valid():
            asignacion = form.save()
            messages.success(request, "Usuario asignado correctamente.")
            return redirect("asociaciones:asociacion_usuarios", pk=asociacion.pk)
    else:
        form = AsociacionUsuarioForm(initial={"asociacion": asociacion})
    asignaciones = asociacion.usuarios.select_related("usuario")
    return render(
        request,
        "asociaciones_app/asociacion_usuarios.html",
        {"asociacion": asociacion, "form": form, "asignaciones": asignaciones},
    )


@login_required
def mis_asociaciones(request):
    if is_admin(request.user):
        asociaciones = Asociacion.objects.all()
    else:
        asociaciones = Asociacion.objects.filter(usuarios__usuario=request.user, usuarios__activo=True)
    return render(
        request,
        "asociaciones_app/mis_asociaciones.html",
        {"asociaciones": asociaciones, "es_admin": is_admin(request.user)},
    )


@login_required
def expediente_caimus(request, pk):
    asociacion = get_object_or_404(Asociacion, pk=pk)
    if not usuario_puede_ver_asociacion(request.user, asociacion):
        raise PermissionDenied

    expediente, creado = ExpedienteCAIMUS.objects.get_or_create(
        asociacion=asociacion,
        defaults={"creado_por": request.user, "actualizado_por": request.user},
    )
    crear_items_expediente(expediente)

    if request.method == "POST":
        form = ExpedienteCAIMUSForm(request.POST, instance=expediente)
        formset = ItemChecklistFormSet(request.POST, instance=expediente)
        if form.is_valid() and formset.is_valid():
            expediente = form.save(commit=False)
            expediente.actualizado_por = request.user
            expediente.save()
            formset.save()
            if request.POST.get("save_item"):
                messages.success(request, "Observación guardada correctamente.")
            else:
                messages.success(request, "Datos guardados correctamente.")
            return redirect("asociaciones:expediente_caimus", pk=asociacion.pk)
    else:
        form = ExpedienteCAIMUSForm(instance=expediente)
        formset = ItemChecklistFormSet(instance=expediente)

    progress = expediente.progress_stats()
    section1_enabled = progress["sections"][1]["done"] == progress["sections"][1]["total"]
    section2_enabled = progress["sections"][2]["done"] == progress["sections"][2]["total"]

    section_forms: Dict[int, List] = {1: [], 2: [], 3: []}
    for form_item in formset.forms:
        section_forms[form_item.instance.seccion].append(form_item)

    return render(
        request,
        "asociaciones_app/expediente_caimus_form.html",
        {
            "asociacion": asociacion,
            "expediente": expediente,
            "form": form,
            "formset": formset,
            "section_forms": section_forms,
            "progress": progress,
            "section1_enabled": section1_enabled,
            "section2_enabled": section2_enabled,
            "es_admin": is_admin(request.user),
        },
    )


def _section_completa(expediente: ExpedienteCAIMUS, seccion: int) -> bool:
    return expediente.items.filter(seccion=seccion).exclude(pdf="").exclude(pdf__isnull=True).count() == expediente.items.filter(
        seccion=seccion
    ).count()


@login_required
@require_POST
def item_upload(request, expediente_id, item_id):
    expediente = get_object_or_404(ExpedienteCAIMUS, pk=expediente_id)
    if not usuario_puede_ver_asociacion(request.user, expediente.asociacion):
        raise PermissionDenied
    item = get_object_or_404(expediente.items, pk=item_id)
    archivo = request.FILES.get("pdf")
    if not archivo:
        messages.error(request, "Debe seleccionar un archivo PDF.")
        return redirect("asociaciones:expediente_caimus", pk=expediente.asociacion.pk)

    if item.seccion == 2 and not _section_completa(expediente, 1):
        messages.error(request, "La sección 2 está bloqueada hasta completar la sección 1.")
        return redirect("asociaciones:expediente_caimus", pk=expediente.asociacion.pk)
    if item.seccion == 3 and not _section_completa(expediente, 2):
        messages.error(request, "La sección 3 está bloqueada hasta completar la sección 2.")
        return redirect("asociaciones:expediente_caimus", pk=expediente.asociacion.pk)

    item.pdf = archivo
    try:
        item.full_clean()
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
        return redirect("asociaciones:expediente_caimus", pk=expediente.asociacion.pk)
    item.save()
    messages.success(request, "Archivo subido correctamente.")
    return redirect("asociaciones:expediente_caimus", pk=expediente.asociacion.pk)


@login_required
@require_POST
def item_observacion(request, expediente_id, item_id):
    expediente = get_object_or_404(ExpedienteCAIMUS, pk=expediente_id)
    if not usuario_puede_ver_asociacion(request.user, expediente.asociacion):
        raise PermissionDenied
    item = get_object_or_404(expediente.items, pk=item_id)
    item.observaciones = request.POST.get("observaciones", "")
    item.save()
    messages.success(request, "Observación guardada correctamente.")
    return redirect("asociaciones:expediente_caimus", pk=expediente.asociacion.pk)


@login_required
@admin_required
def expediente_revision(request, pk):
    expediente = get_object_or_404(ExpedienteCAIMUS, pk=pk)
    estado_anterior = expediente.estado

    if request.method == "POST":
        form = RevisionExpedienteForm(request.POST, instance=expediente)
        if form.is_valid():
            expediente = form.save(commit=False)
            if expediente.estado == ExpedienteCAIMUS.ESTADO_APROBADO:
                expediente.aprobado_por = request.user
                expediente.aprobado_en = timezone.now()
                expediente.observacion_admin = ""
            else:
                expediente.aprobado_por = None
                expediente.aprobado_en = None
            expediente.actualizado_por = request.user
            expediente.save()

            ExpedienteEstadoHistorial.objects.create(
                expediente=expediente,
                estado_anterior=estado_anterior,
                estado_nuevo=expediente.estado,
                observacion=expediente.observacion_admin,
                cambiado_por=request.user,
            )

            if expediente.estado == ExpedienteCAIMUS.ESTADO_APROBADO and not hasattr(expediente, "resolucion"):
                correlativo = generar_correlativo(expediente.asociacion.anio.anio)
                ResolucionExpediente.objects.create(
                    expediente=expediente,
                    correlativo=correlativo,
                    fecha_emision=timezone.now().date(),
                    generado_por=request.user,
                    contenido_snapshot={
                        "asociacion": expediente.asociacion.nombre,
                        "anio": expediente.asociacion.anio.anio,
                        "estado": expediente.estado,
                    },
                )

            messages.success(request, "Estado actualizado correctamente.")
            return redirect("asociaciones:expediente_caimus", pk=expediente.asociacion.pk)
    else:
        form = RevisionExpedienteForm(instance=expediente)

    return render(
        request,
        "asociaciones_app/expediente_revision.html",
        {"expediente": expediente, "form": form},
    )


@login_required
@admin_required
def bandeja_revision(request):
    estado = request.GET.get("estado")
    anio_id = request.GET.get("anio")
    asociaciones = Asociacion.objects.select_related("anio")
    expedientes = ExpedienteCAIMUS.objects.select_related("asociacion", "asociacion__anio")
    if estado:
        expedientes = expedientes.filter(estado=estado)
    if anio_id:
        expedientes = expedientes.filter(asociacion__anio_id=anio_id)

    anios = Anio.objects.all()
    return render(
        request,
        "asociaciones_app/bandeja_revision.html",
        {
            "expedientes": expedientes,
            "anios": anios,
            "estado": estado,
            "anio_id": anio_id,
            "estados": ExpedienteCAIMUS.ESTADOS,
        },
    )


@login_required
@admin_required
def asignaciones_list(request):
    anio_id = request.GET.get("anio")
    asignaciones = AsociacionUsuario.objects.select_related("asociacion", "asociacion__anio", "usuario")
    if anio_id:
        asignaciones = asignaciones.filter(asociacion__anio_id=anio_id)
    anios = Anio.objects.all()
    return render(
        request,
        "asociaciones_app/asignaciones_list.html",
        {"asignaciones": asignaciones, "anios": anios, "anio_id": anio_id},
    )


@login_required
def resolucion_pdf(request, pk):
    expediente = get_object_or_404(ExpedienteCAIMUS, pk=pk)

    if is_admin(request.user):
        permitido = expediente.estado == ExpedienteCAIMUS.ESTADO_APROBADO
    else:
        asignacion = obtener_asignacion_activa(request.user, expediente.asociacion)
        permitido = bool(asignacion and expediente.estado == ExpedienteCAIMUS.ESTADO_APROBADO)

    if not permitido:
        raise PermissionDenied

    resolucion = getattr(expediente, "resolucion", None)

    if not is_admin(request.user) and resolucion is None:
        messages.warning(request, "La resolución aún no ha sido emitida por el administrador.")
        return redirect("asociaciones:expediente_caimus", pk=expediente.asociacion.pk)

    if is_admin(request.user) and resolucion is None:
        correlativo = generar_correlativo(expediente.asociacion.anio.anio)
        resolucion = ResolucionExpediente.objects.create(
            expediente=expediente,
            correlativo=correlativo,
            fecha_emision=timezone.now().date(),
            generado_por=request.user,
            contenido_snapshot={
                "asociacion": expediente.asociacion.nombre,
                "anio": expediente.asociacion.anio.anio,
                "estado": expediente.estado,
            },
        )

    html = render_to_string(
        "asociaciones_app/resolucion_pdf.html",
        {
            "expediente": expediente,
            "resolucion": resolucion,
            "items": expediente.items.all(),
        },
        request=request,
    )

    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f"inline; filename=Resolucion-{resolucion.correlativo}.pdf"
    return response
