from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models, transaction


PDF_VALIDATOR = FileExtensionValidator(["pdf"])


def validate_pdf_size(value):
    max_size = getattr(settings, "CAIMUS_PDF_MAX_SIZE", 5 * 1024 * 1024)
    if value.size > max_size:
        raise ValidationError(f"El archivo excede el tamaño máximo permitido ({max_size // (1024 * 1024)} MB).")


class Anio(models.Model):
    anio = models.PositiveIntegerField(unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Año"
        verbose_name_plural = "Años"
        ordering = ["-anio"]

    def __str__(self) -> str:
        return str(self.anio)


class Asociacion(models.Model):
    anio = models.ForeignKey(Anio, on_delete=models.CASCADE, related_name="asociaciones")
    nombre = models.CharField(max_length=255)
    codigo = models.SlugField(max_length=80)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Asociación"
        verbose_name_plural = "Asociaciones"
        constraints = [
            models.UniqueConstraint(fields=["anio", "codigo"], name="unique_asociacion_codigo_por_anio"),
        ]
        ordering = ["anio", "nombre"]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.anio})"


class AsociacionUsuario(models.Model):
    asociacion = models.ForeignKey(Asociacion, on_delete=models.CASCADE, related_name="usuarios")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="asignaciones_asociacion")
    rol_en_asociacion = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Asignación de usuario"
        verbose_name_plural = "Asignaciones de usuarios"
        constraints = [
            models.UniqueConstraint(fields=["asociacion", "usuario"], name="unique_usuario_asociacion"),
        ]
        ordering = ["-creado_en"]

    def clean(self) -> None:
        super().clean()
        if self.activo and self.usuario_id and self.asociacion_id:
            existe_activo = AsociacionUsuario.objects.filter(
                usuario=self.usuario,
                asociacion__anio=self.asociacion.anio,
                activo=True,
            ).exclude(pk=self.pk)
            if existe_activo.exists():
                raise ValidationError("El usuario ya tiene una asignación activa para este año.")

    def __str__(self) -> str:
        return f"{self.usuario} - {self.asociacion}"


class ExpedienteCAIMUS(models.Model):
    ESTADO_BORRADOR = "BORRADOR"
    ESTADO_EN_REVISION = "EN_REVISION"
    ESTADO_APROBADO = "APROBADO"
    ESTADO_RECHAZADO = "RECHAZADO"

    ESTADOS = [
        (ESTADO_BORRADOR, "Borrador"),
        (ESTADO_EN_REVISION, "En revisión"),
        (ESTADO_APROBADO, "Aprobado"),
        (ESTADO_RECHAZADO, "Rechazado"),
    ]

    asociacion = models.OneToOneField(Asociacion, on_delete=models.CASCADE, related_name="expediente_caimus")
    institucion = models.CharField(max_length=255, blank=True)
    representante_legal = models.CharField(max_length=255, blank=True)
    obs_general = models.TextField(blank=True)
    recomendaciones = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_BORRADOR)
    observacion_admin = models.TextField(blank=True)
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_aprobados",
    )
    aprobado_en = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_creados",
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expedientes_actualizados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Expediente CAIMUS"
        verbose_name_plural = "Expedientes CAIMUS"

    def __str__(self) -> str:
        return f"Expediente {self.asociacion}"

    def is_print_enabled(self) -> bool:
        return self.estado == self.ESTADO_APROBADO

    def progress_stats(self) -> Dict[str, object]:
        items = self.items.all()
        total = items.count()
        completados = items.filter(entregado=True).exclude(pdf="").exclude(pdf__isnull=True).count()
        sections: Dict[int, Dict[str, int]] = {}
        for section in (1, 2, 3):
            section_items = items.filter(seccion=section)
            section_total = section_items.count()
            section_done = section_items.filter(entregado=True).exclude(pdf="").exclude(pdf__isnull=True).count()
            sections[section] = {
                "done": section_done,
                "total": section_total,
                "percent": int((section_done / section_total) * 100) if section_total else 0,
            }
        return {
            "total": total,
            "done": completados,
            "percent": int((completados / total) * 100) if total else 0,
            "sections": sections,
        }


@dataclass(frozen=True)
class ChecklistItemDefinition:
    numero: int
    seccion: int
    titulo: str
    hint: str


CHECKLIST_ITEMS: List[ChecklistItemDefinition] = [
    ChecklistItemDefinition(1, 1, "Documento de constitución", "Acta o documento legal de la asociación."),
    ChecklistItemDefinition(2, 1, "Nombramiento de junta directiva", "Documento vigente de nombramiento."),
    ChecklistItemDefinition(3, 1, "Representación legal", "Identificación del representante legal."),
    ChecklistItemDefinition(4, 1, "NIT de la asociación", "Constancia vigente."),
    ChecklistItemDefinition(5, 1, "Patente de comercio", "Si aplica."),
    ChecklistItemDefinition(6, 1, "Plan de trabajo anual", "Documento firmado."),
    ChecklistItemDefinition(7, 1, "Presupuesto aprobado", "Detalle financiero anual."),
    ChecklistItemDefinition(8, 1, "Estado financiero", "Último estado financiero disponible."),
    ChecklistItemDefinition(9, 2, "Informe de actividades", "Resumen de actividades ejecutadas."),
    ChecklistItemDefinition(10, 2, "Informe de cumplimiento", "Detalle de objetivos alcanzados."),
    ChecklistItemDefinition(11, 2, "Informe de auditoría", "Si aplica, con dictamen."),
    ChecklistItemDefinition(12, 2, "Listado de beneficiarios", "Detalle de beneficiarios del período."),
    ChecklistItemDefinition(13, 2, "Convenios vigentes", "Convenios activos con entidades."),
    ChecklistItemDefinition(14, 2, "Otros respaldos", "Documentación adicional relevante."),
    ChecklistItemDefinition(15, 3, "Acta de aprobación", "Acta de aprobación del expediente."),
    ChecklistItemDefinition(16, 3, "Informe final", "Informe final del período."),
    ChecklistItemDefinition(17, 3, "Compromisos", "Compromisos asumidos por la asociación."),
]


class ItemChecklistCAIMUS(models.Model):
    expediente = models.ForeignKey(ExpedienteCAIMUS, on_delete=models.CASCADE, related_name="items")
    numero = models.PositiveIntegerField()
    seccion = models.PositiveIntegerField()
    titulo = models.CharField(max_length=255)
    hint = models.TextField(blank=True)
    entregado = models.BooleanField(default=False)
    pdf = models.FileField(
        upload_to="caimus/%Y/",
        blank=True,
        null=True,
        validators=[PDF_VALIDATOR, validate_pdf_size],
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Item checklist CAIMUS"
        verbose_name_plural = "Items checklist CAIMUS"
        constraints = [
            models.UniqueConstraint(fields=["expediente", "numero"], name="unique_item_por_expediente"),
        ]
        ordering = ["numero"]

    def __str__(self) -> str:
        return f"{self.numero}. {self.titulo}"


class ExpedienteEstadoHistorial(models.Model):
    expediente = models.ForeignKey(ExpedienteCAIMUS, on_delete=models.CASCADE, related_name="historial_estados")
    estado_anterior = models.CharField(max_length=20, choices=ExpedienteCAIMUS.ESTADOS)
    estado_nuevo = models.CharField(max_length=20, choices=ExpedienteCAIMUS.ESTADOS)
    observacion = models.TextField(blank=True)
    cambiado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    cambiado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial de estado"
        verbose_name_plural = "Historial de estados"
        ordering = ["-cambiado_en"]

    def __str__(self) -> str:
        return f"{self.expediente} {self.estado_anterior} -> {self.estado_nuevo}"


class ResolucionExpediente(models.Model):
    expediente = models.OneToOneField(ExpedienteCAIMUS, on_delete=models.CASCADE, related_name="resolucion")
    correlativo = models.CharField(max_length=30, unique=True)
    fecha_emision = models.DateField()
    generado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    generado_en = models.DateTimeField(auto_now_add=True)
    archivo_pdf = models.FileField(upload_to="resoluciones/%Y/", null=True, blank=True)
    contenido_snapshot = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "Resolución"
        verbose_name_plural = "Resoluciones"

    def __str__(self) -> str:
        return self.correlativo


def crear_items_expediente(expediente: ExpedienteCAIMUS) -> None:
    existentes = set(expediente.items.values_list("numero", flat=True))
    items_to_create = []
    for item in CHECKLIST_ITEMS:
        if item.numero in existentes:
            continue
        items_to_create.append(
            ItemChecklistCAIMUS(
                expediente=expediente,
                numero=item.numero,
                seccion=item.seccion,
                titulo=item.titulo,
                hint=item.hint,
            )
        )
    if items_to_create:
        ItemChecklistCAIMUS.objects.bulk_create(items_to_create)


def generar_correlativo(anio: int) -> str:
    with transaction.atomic():
        ultimo = (
            ResolucionExpediente.objects.select_for_update()
            .filter(expediente__asociacion__anio__anio=anio)
            .order_by("-correlativo")
            .first()
        )
        secuencia = 1
        if ultimo:
            try:
                secuencia = int(ultimo.correlativo.split("-")[-1]) + 1
            except (ValueError, IndexError):
                secuencia = 1
        return f"UPCV-CAIMUS-{anio}-{secuencia:04d}"
