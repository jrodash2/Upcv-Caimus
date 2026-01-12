from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

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
        total = len(CHECKLIST_ITEMS)
        completados = items.exclude(pdf="").exclude(pdf__isnull=True).count()
        return {
            "total": total,
            "done": completados,
            "percent": int((completados / total) * 100) if total else 0,
        }


@dataclass(frozen=True)
class ChecklistItemDefinition:
    numero: int
    seccion: int
    titulo: str
    hint: str


CHECKLIST_ITEMS: List[ChecklistItemDefinition] = [
    ChecklistItemDefinition(1, 1, "Solicitud dirigida al señor Ministro de Gobernación", ""),
    ChecklistItemDefinition(2, 1, "Plan Operativo Anual -POA-", ""),
    ChecklistItemDefinition(
        3,
        1,
        "Copia legalizada del Testimonio de la Escritura Pública Constitutiva de la entidad",
        "",
    ),
    ChecklistItemDefinition(4, 1, "Constancia de inscripción y actualización de datos -RTU-", ""),
    ChecklistItemDefinition(5, 1, "Solvencia Fiscal vigente", ""),
    ChecklistItemDefinition(
        6,
        1,
        "Constancia de Inventario de Cuentas emitida por el Ministerio de Finanzas Públicas.",
        "",
    ),
    ChecklistItemDefinition(
        7,
        1,
        "Certificación de la constancia de inscripción de la entidad en el Registro de Personas Jurídicas -REPEJU-",
        "",
    ),
    ChecklistItemDefinition(8, 1, "Copia legalizada -DPI- de representante legal", ""),
    ChecklistItemDefinition(
        9,
        1,
        "Copia legalizada del Acta Notarial de nombramiento de representante legal",
        "",
    ),
    ChecklistItemDefinition(
        10,
        1,
        "Constancia de inscripción y actualización de datos -RTU- del representante legal",
        "",
    ),
    ChecklistItemDefinition(11, 1, "Solvencia Fiscal vigente, del Representante Legal", ""),
    ChecklistItemDefinition(
        12,
        1,
        "Certificación de la constancia de inscripción en el Registro de Personas Jurídicas -REPEJU-",
        "",
    ),
]


class ItemChecklistCAIMUS(models.Model):
    SECCION_1 = 1
    SECCION_2 = 2
    SECCION_3 = 3
    SECCION_CHOICES = [
        (SECCION_1, "Sección 1"),
        (SECCION_2, "Sección 2"),
        (SECCION_3, "Sección 3"),
    ]

    expediente = models.ForeignKey(ExpedienteCAIMUS, on_delete=models.CASCADE, related_name="items")
    numero = models.PositiveIntegerField()
    seccion = models.PositiveIntegerField(choices=SECCION_CHOICES, default=SECCION_1)
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
            models.CheckConstraint(
                check=models.Q(seccion__in=[1, 2, 3]),
                name="itemchecklist_seccion_valida",
            ),
        ]
        ordering = ["numero"]

    def save(self, *args, **kwargs) -> None:
        self.entregado = bool(self.pdf)
        super().save(*args, **kwargs)

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
    existentes = {item.numero: item for item in expediente.items.all()}
    numeros_validos = {item.numero for item in CHECKLIST_ITEMS}
    items_to_create = []
    items_to_update = []
    for item in CHECKLIST_ITEMS:
        existente = existentes.get(item.numero)
        if existente is None:
            items_to_create.append(
                ItemChecklistCAIMUS(
                    expediente=expediente,
                    numero=item.numero,
                    seccion=item.seccion,
                    titulo=item.titulo,
                    hint=item.hint,
                )
            )
            continue
        actualizado = False
        if existente.seccion != item.seccion:
            existente.seccion = item.seccion
            actualizado = True
        if existente.titulo != item.titulo:
            existente.titulo = item.titulo
            actualizado = True
        if existente.hint != item.hint:
            existente.hint = item.hint
            actualizado = True
        if actualizado:
            items_to_update.append(existente)
    if items_to_create:
        ItemChecklistCAIMUS.objects.bulk_create(items_to_create)
    if items_to_update:
        ItemChecklistCAIMUS.objects.bulk_update(items_to_update, ["seccion", "titulo", "hint"])
    extra_items = expediente.items.exclude(numero__in=numeros_validos)
    if extra_items.exists():
        extra_items.delete()


MESES_CHOICES = [
    (1, "Enero"),
    (2, "Febrero"),
    (3, "Marzo"),
    (4, "Abril"),
    (5, "Mayo"),
    (6, "Junio"),
    (7, "Julio"),
    (8, "Agosto"),
    (9, "Septiembre"),
    (10, "Octubre"),
    (11, "Noviembre"),
    (12, "Diciembre"),
]


class InformeMensual(models.Model):
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

    asociacion = models.ForeignKey(Asociacion, on_delete=models.CASCADE, related_name="informes_mensuales")
    mes = models.PositiveSmallIntegerField(choices=MESES_CHOICES)
    pdf = models.FileField(
        upload_to="informes/%Y/%m/",
        blank=True,
        null=True,
        validators=[PDF_VALIDATOR, validate_pdf_size],
    )
    observaciones_usuario = models.TextField(blank=True)
    estado = models.CharField(choices=ESTADOS, default=ESTADO_BORRADOR, max_length=20)
    observacion_admin = models.TextField(blank=True)
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="informes_aprobados",
    )
    aprobado_en = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="informes_creados",
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="informes_actualizados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Informe mensual"
        verbose_name_plural = "Informes mensuales"
        constraints = [
            models.UniqueConstraint(fields=["asociacion", "mes"], name="unique_informe_mes_asociacion"),
        ]
        ordering = ["mes"]

    def __str__(self) -> str:
        return f"{self.asociacion} - {self.get_mes_display()}"

    def save(self, *args, **kwargs) -> None:
        if self.pdf and self.estado == self.ESTADO_BORRADOR:
            self.estado = self.ESTADO_EN_REVISION
        super().save(*args, **kwargs)


class InformeEstadoHistorial(models.Model):
    informe = models.ForeignKey(InformeMensual, on_delete=models.CASCADE, related_name="historial_estados")
    estado_anterior = models.CharField(max_length=20, choices=InformeMensual.ESTADOS)
    estado_nuevo = models.CharField(max_length=20, choices=InformeMensual.ESTADOS)
    observacion = models.TextField(blank=True)
    cambiado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    cambiado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial de estado de informe"
        verbose_name_plural = "Historial de estados de informes"
        ordering = ["-cambiado_en"]

    def __str__(self) -> str:
        return f"{self.informe} {self.estado_anterior} -> {self.estado_nuevo}"


def crear_informes_mensuales(asociacion: Asociacion, usuario: Optional[models.Model] = None) -> None:
    existentes = set(asociacion.informes_mensuales.values_list("mes", flat=True))
    informes = []
    for mes, _label in MESES_CHOICES:
        if mes in existentes:
            continue
        informes.append(
            InformeMensual(
                asociacion=asociacion,
                mes=mes,
                creado_por=usuario,
                actualizado_por=usuario,
            )
        )
    if informes:
        InformeMensual.objects.bulk_create(informes)


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
