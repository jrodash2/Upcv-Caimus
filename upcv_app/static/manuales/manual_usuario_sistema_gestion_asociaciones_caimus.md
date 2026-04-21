# 1. PORTADA

## Sistema de Gestión de Asociaciones CAIMUS

**Manual de Usuario**

**Descripción breve:**
Plataforma web institucional para la gestión anual de asociaciones, expedientes CAIMUS, revisión administrativa, control de informes mensuales y emisión de resoluciones/constancias en PDF.

**Fecha:** 21 de abril de 2026  
**Institución:** UPCV

---

# 2. INTRODUCCIÓN

## ¿Qué es el sistema?
El **Sistema de Gestión de Asociaciones CAIMUS** es una aplicación web que organiza, en un solo lugar, el ciclo de trabajo entre:

- La **Asociación** (que carga documentación y envía a revisión), y
- El **Administrador** (que revisa, aprueba o rechaza y genera resoluciones).

El sistema trabaja por **año**, y permite administrar:

1. Asociaciones.
2. Expedientes CAIMUS.
3. Checklist de documentos por año.
4. Informes mensuales (narrativo y presupuestario).
5. Bandeja de revisión.
6. Notificaciones y alertas.

## Objetivo del sistema
Facilitar el proceso institucional para:

1. Recibir y ordenar documentación en formato PDF.
2. Controlar estados de revisión.
3. Dar trazabilidad mediante historial y observaciones.
4. Emitir documentos de respaldo (resolución de expediente y constancia de informe mensual).

## ¿A quién va dirigido?
Este manual está dirigido a:

1. **Administrador**: personal que administra años, asociaciones, checklist, revisión y aprobaciones.
2. **Usuario Asociación**: personal asignado a una asociación para cargar documentos y enviar expedientes/informes.

---

# 3. ACCESO AL SISTEMA

## Cómo iniciar sesión
1. Abra el enlace institucional del sistema en su navegador.
2. Se mostrará la pantalla **Iniciar Sesión**.
3. Ingrese:
   - **Usuario**
   - **Contraseña**
4. Presione el botón **Entrar**.

## Pantalla de login
En la pantalla de inicio verá:

- Título de ingreso al sistema.
- Campo de usuario.
- Campo de contraseña.
- Botón **Entrar**.

Si las credenciales no son correctas, el sistema mostrará un mensaje de error.

## Recuperación de acceso (si aplica)
El proyecto tiene rutas para recuperación de contraseña mediante flujo de restablecimiento por correo.

Si su institución habilitó este proceso:
1. Solicite al administrador el acceso al enlace de recuperación.
2. Ingrese su correo/usuario según la configuración institucional.
3. Siga el enlace de restablecimiento enviado.
4. Defina una nueva contraseña y vuelva a iniciar sesión.

> Nota: en la pantalla de login principal no siempre aparece el enlace directo de “Olvidé mi contraseña”. Si no lo ve, solicite apoyo al Administrador.

---

# 4. ROLES DEL SISTEMA

## 4.1 Administrador
El Administrador puede:

1. Crear y editar **años**.
2. Configurar el **checklist anual** de documentos.
3. Crear y editar **asociaciones**.
4. Asignar **usuarios** a asociaciones.
5. Ver dashboards globales con métricas y alertas.
6. Revisar expedientes e informes.
7. Aprobar o rechazar con observaciones.
8. Emitir/generar resoluciones y constancias.
9. Gestionar la **bandeja de revisión**.

## 4.2 Usuario Asociación
El Usuario Asociación puede:

1. Ver únicamente sus asociaciones asignadas.
2. Completar datos del expediente CAIMUS.
3. Cargar y re-subir PDFs del checklist.
4. Enviar expediente a revisión cuando esté completo.
5. Cargar informes mensuales (narrativo y presupuestario).
6. Enviar informes a revisión.
7. Consultar observaciones del Administrador.
8. Descargar resolución/constancia cuando corresponda.
9. Marcar alertas como leídas.

---

# 5. PANEL PRINCIPAL (DASHBOARD)

## Descripción general
Al ingresar, el sistema muestra un **Dashboard**. El contenido cambia según el rol:

- **Administrador:** vista global institucional.
- **Asociación:** vista de su(s) asociación(es) y su avance.

## Métricas
### Para Administrador
Puede ver indicadores como:

1. Años activos.
2. Total de asociaciones.
3. Expedientes aprobados.
4. Informes pendientes.
5. Usuarios asignados.
6. Resoluciones emitidas.

### Para Asociación
Puede ver indicadores como:

1. Total de asociaciones asignadas.
2. Estado del expediente.
3. Documentos cargados y pendientes.
4. Informes aprobados y pendientes.
5. Alertas nuevas.
6. Porcentaje de cumplimiento.

## Alertas
- El Administrador visualiza alertas nuevas con botón **Revisar**.
- La Asociación ve actividad reciente y notificaciones en su dashboard.

## Filtros por año
1. Ubique el selector **Filtrar por año**.
2. Elija el año deseado.
3. El sistema actualiza indicadores y tablas según ese año.
4. Si el usuario tiene varias asociaciones, también puede filtrar por asociación.

---

# 6. GESTIÓN DE ASOCIACIONES

## Cómo ver asociaciones
### Usuario Asociación
1. Ingrese a **Mis asociaciones**.
2. Verá tarjetas con:
   - Nombre
   - Año
   - Código
   - Alertas recientes
3. Use botones:
   - **Expediente**
   - **Informes**

### Administrador
1. Puede acceder a todas las asociaciones desde listados por año.
2. También puede entrar a **Mis asociaciones** para navegación rápida.

## Cómo cambiar entre asociaciones (si aplica)
Si tiene más de una asociación asignada:

1. Desde el dashboard, ubique **Ver información de la asociación**.
2. Seleccione la asociación en el desplegable.
3. El panel se actualizará con la información de esa asociación.

---

# 7. EXPEDIENTE CAIMUS

## Qué es un expediente
Es el registro principal anual de una asociación donde se consolidan:

1. Datos generales.
2. Checklist de documentos requeridos.
3. Observaciones de revisión.
4. Estado formal del proceso.

## Estructura del expediente
El expediente está dividido en:

1. **Datos Generales**.
2. **Checklist de documentos** (con carga PDF por ítem).
3. **Progreso** (completados, pendientes, porcentaje).
4. **Resolución** (descarga cuando aplica).
5. **Observación del administrador**.
6. **Historial de estados**.

## Estados del expediente
El expediente puede estar en:

1. **Borrador**: en preparación.
2. **En revisión**: enviado para revisión administrativa.
3. **Aprobado**: validado por administrador.
4. **Rechazado**: requiere correcciones.

---

## 7.1 Datos Generales

### Cómo llenar
1. Ingrese al módulo **Expediente** de su asociación.
2. Complete los campos visibles:
   - Institución
   - Representante legal
   - Observaciones generales
   - Recomendaciones

### Cómo guardar
1. Presione **Guardar datos generales** (o **Guardar todo**).
2. Espere el mensaje de confirmación.
3. Verifique que la información quede visible tras recargar la página.

---

## 7.2 Checklist de Documentos

### Cómo subir archivos
1. En la sección **Checklist**, abra el ítem correspondiente.
2. Presione **Seleccionar archivo**.
3. Elija un archivo **PDF**.
4. Haga clic en **Subir archivo**.
5. Confirme que el estado del ítem cambie a **Subido**.

### Cómo re-subir
1. Abra el ítem con archivo ya cargado.
2. Seleccione un nuevo PDF.
3. Use el botón **Re-subir archivo**.
4. El nuevo archivo reemplazará el anterior.

### Observaciones
- Cada ítem tiene un campo de observaciones.
- Puede escribir notas y presionar **Guardar observación**.

### Estados de cada ítem
Cada requisito se visualiza como:

1. **Subido** (cuando tiene PDF cargado).
2. **Pendiente** (cuando aún no hay PDF).

---

## 7.3 Enviar a revisión

### Cuándo usarlo
Use **Enviar a revisión** únicamente cuando:

1. Todos los documentos requeridos estén cargados.
2. Los datos generales estén correctos.
3. El expediente esté en **Borrador** o **Rechazado**.

### Qué sucede
1. El estado cambia a **En revisión**.
2. Se registra el movimiento en historial.
3. Se notifica al Administrador.
4. Se crea entrada en bandeja de revisión.

---

## 7.4 Revisión por Administrador

### Aprobar
1. El Administrador abre el expediente.
2. Revisa documentos, observaciones e historial.
3. En **Panel de revisión**, presiona **Aprobar**.
4. El expediente cambia a estado **Aprobado**.

### Rechazar
1. El Administrador ingresa observación de rechazo.
2. Presiona **Rechazar**.
3. El expediente cambia a estado **Rechazado**.
4. La asociación recibe notificación para corrección.

### Observaciones
- El administrador puede registrar/actualizar observación administrativa.
- La asociación la ve en el panel lateral del expediente.

---

## 7.5 Resolución

### Cuándo se genera
La resolución de expediente se gestiona cuando el expediente está **Aprobado**.

### Cómo descargarla
### Para Asociación
1. Abra su expediente aprobado.
2. En la tarjeta **Resolución**, presione **Descargar Resolución PDF**.

### Para Administrador
1. Puede ingresar a la ruta de resolución del expediente aprobado.
2. El sistema muestra el PDF de resolución.

> Nota importante: para usuarios de asociación, además de estar aprobado, el expediente debe estar completo para descargar.

---

# 8. INFORMES MENSUALES

## Descripción general
Cada asociación dispone de un módulo anual con **12 meses** (enero a diciembre).

Para cada mes se manejan:
1. Informe narrativo (PDF).
2. Informe presupuestario (PDF).
3. Estado del informe mensual.

---

## 8.1 Estructura de cada mes

### Informe narrativo
Documento descriptivo del avance mensual en formato PDF.

### Informe presupuestario
Documento financiero/presupuestario del mes en formato PDF.

---

## 8.2 Carga de archivos

### Cómo subir PDFs
1. Entre a **Informes** de la asociación.
2. Abra el mes deseado.
3. En “Informe narrativo”, seleccione PDF y pulse **Subir narrativo**.
4. En “Informe presupuestario”, seleccione PDF y pulse **Subir presupuestario**.
5. Verifique que ambos aparezcan como **Subido**.

### Diferencia entre cargar y enviar a revisión
- **Cargar**: solo guarda o actualiza archivos en el sistema.
- **Enviar a revisión**: cambia el estado y notifica al Administrador para evaluación.

> Si un informe estaba aprobado o rechazado y la asociación vuelve a cargar archivo, el informe regresa a borrador.

---

## 8.3 Enviar informe a revisión

### Funcionamiento correcto
1. Confirme que el mes tenga **ambos archivos** (narrativo y presupuestario).
2. Presione **Enviar a revisión**.
3. El estado pasará a **En revisión**.
4. El Administrador recibirá alerta y entrada en bandeja.

---

## 8.4 Revisión de informes

### Aprobación
1. El Administrador abre el informe mensual.
2. Revisa ambos documentos.
3. Presiona **Aprobar**.
4. El estado cambia a **Aprobado**.
5. El sistema genera registro de resolución/constancia.

### Rechazo
1. El Administrador ingresa observación.
2. Presiona **Rechazar**.
3. El estado cambia a **Rechazado**.
4. Se notifica a la asociación para correcciones.

---

## 8.5 Descarga de constancia
1. Una vez aprobado el informe mensual, aparece el botón de descarga.
2. Presione **Descargar constancia** (o generar/descargar según rol).
3. El sistema abre el PDF de constancia en pantalla.
4. Desde el visor del navegador, descargue o imprima.

---

# 9. BANDEJA DE REVISIÓN (ADMIN)

## Qué muestra
La bandeja muestra elementos enviados por asociaciones para atención administrativa.

## Tipos de elementos
1. **Expediente**.
2. **Informe**.

## Cómo revisar
1. Abra **Bandeja de revisión**.
2. Use filtros por:
   - Tipo
   - Año
   - Estado
3. Presione:
   - **Revisar expediente**, o
   - **Revisar informe**
4. Realice la revisión en el módulo correspondiente.

## Cómo marcar como atendido
1. En la tarjeta de la bandeja, ubique el elemento pendiente.
2. Presione **Marcar atendida**.
3. El estado cambia a **Atendida**.

---

# 10. NOTIFICACIONES Y ALERTAS

## Tipos de alertas
El sistema maneja alertas de tipo:

1. Informativa.
2. Advertencia.
3. Éxito.
4. Error.

## Para administrador
Recibe alertas cuando, por ejemplo:

1. Una asociación envía expediente a revisión.
2. Una asociación envía informe mensual a revisión.
3. Existen nuevos pendientes en la bandeja.

Puede abrir cada alerta con **Revisar**.

## Para asociaciones
Reciben alertas cuando, por ejemplo:

1. El expediente es aprobado/rechazado.
2. El informe mensual es aprobado/rechazado.
3. El administrador registra nuevas observaciones.
4. Se actualiza checklist anual aplicable.

Desde **Mis asociaciones**, puede usar **Marcar alertas como leídas**.

---

# 11. BUENAS PRÁCTICAS

## Recomendaciones de uso
1. Trabaje siempre en el año correcto (ver filtro superior).
2. Nombre sus archivos PDF de forma clara (ejemplo: `poa_2026.pdf`).
3. Verifique cada archivo abriéndolo antes de enviarlo a revisión.
4. Revise observaciones del administrador antes de reenviar.
5. Evite esperar al final del periodo para cargar informes.
6. Mantenga su navegador actualizado.

## Evitar errores comunes
1. No intente enviar a revisión si faltan documentos.
2. No cargue formatos distintos de PDF.
3. No ignore estados de rechazo sin leer observación.
4. No mezcle documentos de meses distintos en un mismo informe.

---

# 12. SOLUCIÓN DE PROBLEMAS

## PDF no carga
**Posibles causas y solución:**

1. El archivo no es PDF.
   - Solución: convierta el archivo a PDF e intente de nuevo.
2. El PDF supera el tamaño permitido.
   - Solución: reduzca tamaño del archivo y vuelva a cargar.
3. Seleccionó el archivo pero no presionó el botón de subida.
   - Solución: pulse **Subir** o **Re-subir** según corresponda.

## No aparece botón enviar a revisión
**Posibles causas y solución:**

1. Estado no permitido.
   - El botón solo aparece en **Borrador** o **Rechazado**.
2. Faltan documentos requeridos.
   - Complete todos los ítems del checklist (expediente).
   - En informes, cargue narrativo + presupuestario.
3. Usuario sin permiso.
   - Verifique que esté ingresando con usuario de asociación asignada.

## No se puede descargar resolución
**Posibles causas y solución:**

1. El expediente/informe aún no está aprobado.
2. El usuario no pertenece a la asociación correspondiente.
3. En expediente, faltan documentos completos para usuario asociación.

**Acción recomendada:**
- Revise estado actual y observaciones.
- Si considera que el estado es incorrecto, contacte al administrador.

## Errores comunes
1. “Mes inválido”
   - Ocurre al intentar operar fuera de los 12 meses permitidos.
2. “Debe seleccionar un archivo PDF”
   - Ocurre cuando se envía formulario sin archivo.
3. “Debes cargar ambos archivos antes de enviar a revisión”
   - Ocurre cuando falta narrativo o presupuestario.
4. “Debe indicar la observación del rechazo”
   - Ocurre al rechazar sin comentario administrativo.

---

# 13. PREGUNTAS FRECUENTES (FAQ)

## 1) ¿Puedo tener más de una asociación asignada?
Sí. Si tiene varias, puede alternarlas desde el dashboard o desde “Mis asociaciones”.

## 2) ¿Qué pasa si subo un archivo incorrecto?
Puede **re-subir** el PDF correcto en el mismo ítem o mes.

## 3) ¿Enviar a revisión es lo mismo que guardar?
No. Guardar conserva cambios. Enviar a revisión inicia evaluación administrativa.

## 4) ¿Quién puede aprobar o rechazar?
Solo el **Administrador**.

## 5) ¿Por qué mi expediente volvió a borrador?
En informes mensuales, al recargar archivos en estados aprobados/rechazados, el sistema vuelve a borrador para nueva revisión.

## 6) ¿Dónde veo observaciones del administrador?
- En expediente: panel de observación administrativa.
- En informes: campo de observación admin del mes.

## 7) ¿Cómo sé que ya me revisaron?
Por cambio de estado (Aprobado/Rechazado) y por notificación/alerta en el sistema.

## 8) ¿Cómo obtengo evidencia de aprobación?
- Expediente: resolución PDF.
- Informe mensual: constancia PDF del mes aprobado.

## 9) ¿Qué hago si no veo ninguna asociación?
Solicite al Administrador que valide su asignación de usuario activa para el año correspondiente.

## 10) ¿Puedo editar checklist como usuario asociación?
No. El checklist anual se configura por el Administrador.

---

**Fin del Manual de Usuario**
