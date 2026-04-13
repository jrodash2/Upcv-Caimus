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


@dataclass(frozen=True)
class ChecklistItemDefinition:
    numero: int
    seccion: int
    titulo: str
    hint: str


DEFAULT_CHECKLIST_ITEMS: List[ChecklistItemDefinition] = [
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


class ChecklistAnioItem(models.Model):
    anio = models.ForeignKey(Anio, on_delete=models.CASCADE, related_name="checklist_items")
    numero = models.PositiveIntegerField()
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Item checklist por año"
        verbose_name_plural = "Items checklist por año"
        constraints = [
            models.UniqueConstraint(fields=["anio", "numero"], name="unique_checklist_anio_numero"),
        ]
        ordering = ["numero"]

    def __str__(self) -> str:
        return f"{self.anio.anio} - {self.numero}. {self.titulo}"


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
        items = self.items.filter(activo=True)
        total = items.count()
        completados = items.exclude(pdf="").exclude(pdf__isnull=True).count()
        return {
            "total": total,
            "done": completados,
            "percent": int((completados / total) * 100) if total else 0,
        }


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
    plantilla_item = models.ForeignKey(
        ChecklistAnioItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items_expediente",
    )
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
    activo = models.BooleanField(default=True)

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


def sincronizar_checklist_expediente(expediente: ExpedienteCAIMUS) -> None:
    plantilla_qs = expediente.asociacion.anio.checklist_items.filter(activo=True).order_by("numero")
    if not plantilla_qs.exists():
        ChecklistAnioItem.objects.bulk_create(
            [
                ChecklistAnioItem(
                    anio=expediente.asociacion.anio,
                    numero=item.numero,
                    titulo=item.titulo,
                    descripcion=item.hint,
                    activo=True,
                )
                for item in DEFAULT_CHECKLIST_ITEMS
            ]
        )
        plantilla_qs = expediente.asociacion.anio.checklist_items.filter(activo=True).order_by("numero")

    plantilla_ids = set(plantilla_qs.values_list("id", flat=True))
    existentes = {
        item.plantilla_item_id: item
        for item in expediente.items.exclude(plantilla_item_id__isnull=True)
    }
    existentes_por_numero = {item.numero: item for item in expediente.items.all()}
    items_to_create = []
    items_to_update = []

    for plantilla_item in plantilla_qs:
        existente = existentes.get(plantilla_item.id) or existentes_por_numero.get(plantilla_item.numero)
        if existente is None:
            items_to_create.append(
                ItemChecklistCAIMUS(
                    expediente=expediente,
                    plantilla_item=plantilla_item,
                    numero=plantilla_item.numero,
                    seccion=ItemChecklistCAIMUS.SECCION_1,
                    titulo=plantilla_item.titulo,
                    hint=plantilla_item.descripcion,
                    activo=True,
                )
            )
            continue

        changed = False
        if existente.plantilla_item_id != plantilla_item.id:
            existente.plantilla_item = plantilla_item
            changed = True
        if existente.numero != plantilla_item.numero:
            existente.numero = plantilla_item.numero
            changed = True
        if existente.titulo != plantilla_item.titulo:
            existente.titulo = plantilla_item.titulo
            changed = True
        if existente.hint != plantilla_item.descripcion:
            existente.hint = plantilla_item.descripcion
            changed = True
        if not existente.activo:
            existente.activo = True
            changed = True
        if changed:
            items_to_update.append(existente)

    for item in expediente.items.all():
        debe_estar_activo = item.plantilla_item_id in plantilla_ids if item.plantilla_item_id else False
        if item.activo != debe_estar_activo:
            item.activo = debe_estar_activo
            items_to_update.append(item)

    if items_to_create:
        ItemChecklistCAIMUS.objects.bulk_create(items_to_create)
    if items_to_update:
        ItemChecklistCAIMUS.objects.bulk_update(
            items_to_update,
            ["plantilla_item", "numero", "titulo", "hint", "activo"],
        )


def crear_items_expediente(expediente: ExpedienteCAIMUS) -> None:
    sincronizar_checklist_expediente(expediente)


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
    archivo_narrativo = models.FileField(
        upload_to="informes/narrativos/%Y/%m/",
        blank=True,
        null=True,
        validators=[PDF_VALIDATOR, validate_pdf_size],
    )
    archivo_presupuestario = models.FileField(
        upload_to="informes/presupuestarios/%Y/%m/",
        blank=True,
        null=True,
        validators=[PDF_VALIDATOR, validate_pdf_size],
    )
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

    def tiene_archivos_completos(self) -> bool:
        return bool(self.archivo_narrativo and self.archivo_presupuestario)

    def save(self, *args, **kwargs) -> None:
        if self.tiene_archivos_completos() and self.estado in [self.ESTADO_BORRADOR, self.ESTADO_RECHAZADO]:
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


class ResolucionInformeMensual(models.Model):
    informe = models.OneToOneField(InformeMensual, on_delete=models.CASCADE, related_name="resolucion")
    correlativo = models.CharField(max_length=50, unique=True)
    fecha_emision = models.DateField()
    generado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    generado_en = models.DateTimeField(auto_now_add=True)
    archivo_pdf = models.FileField(upload_to="resoluciones_informes/%Y/", null=True, blank=True)
    contenido_snapshot = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "Resolución de informe mensual"
        verbose_name_plural = "Resoluciones de informes mensuales"

    def __str__(self) -> str:
        return self.correlativo


class NotificacionAsociacion(models.Model):
    TIPO_INFO = "info"
    TIPO_WARNING = "warning"
    TIPO_SUCCESS = "success"
    TIPO_ERROR = "error"
    TIPOS = [
        (TIPO_INFO, "Info"),
        (TIPO_WARNING, "Warning"),
        (TIPO_SUCCESS, "Success"),
        (TIPO_ERROR, "Error"),
    ]

    asociacion = models.ForeignKey(Asociacion, on_delete=models.CASCADE, related_name="notificaciones")
    titulo = models.CharField(max_length=255)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=30, choices=TIPOS, default=TIPO_INFO)
    leida = models.BooleanField(default=False)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificaciones_asociacion_creadas",
    )
    creada_en = models.DateTimeField(auto_now_add=True)
    enlace = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Notificación de asociación"
        verbose_name_plural = "Notificaciones de asociación"
        ordering = ["-creada_en"]

    def __str__(self) -> str:
        return f"{self.asociacion} - {self.titulo}"


class NotificacionAdmin(models.Model):
    TIPO_INFO = "info"
    TIPO_WARNING = "warning"
    TIPO_SUCCESS = "success"
    TIPO_ERROR = "error"
    TIPOS = [
        (TIPO_INFO, "Info"),
        (TIPO_WARNING, "Warning"),
        (TIPO_SUCCESS, "Success"),
        (TIPO_ERROR, "Error"),
    ]

    titulo = models.CharField(max_length=255)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=30, choices=TIPOS, default=TIPO_INFO)
    leida = models.BooleanField(default=False)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificaciones_admin_creadas",
    )
    creada_en = models.DateTimeField(auto_now_add=True)
    enlace = models.CharField(max_length=255, blank=True)
    asociacion = models.ForeignKey(Asociacion, null=True, blank=True, on_delete=models.CASCADE, related_name="notificaciones_admin")
    informe = models.ForeignKey("InformeMensual", null=True, blank=True, on_delete=models.CASCADE, related_name="notificaciones_admin")

    class Meta:
        verbose_name = "Notificación para administrador"
        verbose_name_plural = "Notificaciones para administrador"
        ordering = ["-creada_en"]

    def __str__(self) -> str:
        return self.titulo


class EntradaRevisionAdmin(models.Model):
    TIPO_EXPEDIENTE = "expediente"
    TIPO_INFORME = "informe"
    TIPOS = [
        (TIPO_EXPEDIENTE, "Expediente"),
        (TIPO_INFORME, "Informe"),
    ]

    ESTADO_PENDIENTE = "pendiente"
    ESTADO_ATENDIDA = "atendida"
    ESTADOS = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_ATENDIDA, "Atendida"),
    ]

    tipo = models.CharField(max_length=20, choices=TIPOS)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_PENDIENTE)
    titulo = models.CharField(max_length=255)
    mensaje = models.TextField()
    asociacion = models.ForeignKey(Asociacion, null=True, blank=True, on_delete=models.CASCADE, related_name="entradas_revision")
    expediente = models.ForeignKey("ExpedienteCAIMUS", null=True, blank=True, on_delete=models.CASCADE, related_name="entradas_revision")
    informe = models.ForeignKey("InformeMensual", null=True, blank=True, on_delete=models.CASCADE, related_name="entradas_revision")
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entradas_revision_admin_creadas",
    )
    creada_en = models.DateTimeField(auto_now_add=True)
    atendida_en = models.DateTimeField(null=True, blank=True)
    enlace = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Entrada de revisión admin"
        verbose_name_plural = "Entradas de revisión admin"
        ordering = ["-creada_en"]

    def __str__(self) -> str:
        return self.titulo


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


def generar_correlativo_informe(anio: int, mes: int) -> str:
    with transaction.atomic():
        ultimo = (
            ResolucionInformeMensual.objects.select_for_update()
            .filter(informe__asociacion__anio__anio=anio, informe__mes=mes)
            .order_by("-correlativo")
            .first()
        )
        secuencia = 1
        if ultimo:
            try:
                secuencia = int(ultimo.correlativo.split("-")[-1]) + 1
            except (ValueError, IndexError):
                secuencia = 1
        return f"UPCV-INF-{anio}-{mes:02d}-{secuencia:04d}"


def crear_notificacion_asociacion(
    asociacion: Asociacion,
    titulo: str,
    mensaje: str,
    tipo: str = NotificacionAsociacion.TIPO_INFO,
    creada_por=None,
    enlace: str = "",
) -> NotificacionAsociacion:
    if tipo not in dict(NotificacionAsociacion.TIPOS):
        tipo = NotificacionAsociacion.TIPO_INFO
    return NotificacionAsociacion.objects.create(
        asociacion=asociacion,
        titulo=titulo,
        mensaje=mensaje,
        tipo=tipo,
        creada_por=creada_por,
        enlace=enlace,
    )


def crear_notificacion_admin(
    titulo: str,
    mensaje: str,
    tipo: str = NotificacionAdmin.TIPO_INFO,
    creada_por=None,
    enlace: str = "",
    asociacion: Optional[Asociacion] = None,
    informe: Optional[InformeMensual] = None,
) -> NotificacionAdmin:
    if tipo not in dict(NotificacionAdmin.TIPOS):
        tipo = NotificacionAdmin.TIPO_INFO
    return NotificacionAdmin.objects.create(
        titulo=titulo,
        mensaje=mensaje,
        tipo=tipo,
        creada_por=creada_por,
        enlace=enlace,
        asociacion=asociacion,
        informe=informe,
    )


def crear_entrada_revision_admin(
    *,
    tipo: str,
    titulo: str,
    mensaje: str,
    enlace: str = "",
    asociacion: Optional[Asociacion] = None,
    expediente: Optional[ExpedienteCAIMUS] = None,
    informe: Optional[InformeMensual] = None,
    creada_por=None,
) -> EntradaRevisionAdmin:
    if tipo not in dict(EntradaRevisionAdmin.TIPOS):
        raise ValidationError("Tipo de entrada inválido.")
    filtros = {
        "tipo": tipo,
        "estado": EntradaRevisionAdmin.ESTADO_PENDIENTE,
        "asociacion": asociacion,
        "expediente": expediente,
        "informe": informe,
    }
    if EntradaRevisionAdmin.objects.filter(**filtros).exists():
        return EntradaRevisionAdmin.objects.filter(**filtros).order_by("-creada_en").first()
    return EntradaRevisionAdmin.objects.create(
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        enlace=enlace,
        asociacion=asociacion,
        expediente=expediente,
        informe=informe,
        creada_por=creada_por,
    )
