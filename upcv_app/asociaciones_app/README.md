# Módulo Asociaciones CAIMUS

## Flujo
1. Administrador crea **Años** y **Asociaciones**.
2. Administrador asigna usuarios a asociaciones con un rol interno.
3. Usuario asignado o administrador completa el **Expediente CAIMUS** y adjunta PDFs.
4. Administrador revisa el expediente y cambia su estado: borrador, en revisión, aprobado o rechazado.
5. Al aprobar, el sistema emite la **Resolución** con correlativo y habilita la descarga en PDF.

## Permisos
- **Administrador**: gestiona años, asociaciones, asignaciones, revisa expedientes y emite resoluciones.
- **Usuario asignado**: ve y edita solo el expediente de su asociación.
- La resolución solo se descarga si el expediente está aprobado; el administrador puede emitirla.

## Rutas principales
- `/asociaciones/anios/`
- `/asociaciones/<anio_id>/lista/`
- `/asociaciones/<id>/usuarios/`
- `/asociaciones/mis-asociaciones/`
- `/asociaciones/<id>/caimus/`
- `/asociaciones/expedientes/<id>/resolucion/pdf/`
