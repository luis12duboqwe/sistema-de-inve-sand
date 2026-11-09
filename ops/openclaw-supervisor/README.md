# OpenClaw SoftMobile — enfoque exclusivo en ventas

**Estado 7 de noviembre de 2026 (Honduras):** el propietario priorizó exclusivamente las ventas de celulares. Reparaciones y productividad del taller están **pausadas**. WhatsApp y el lanzamiento público quedan para la última fase.

**Código de reparaciones conservado de manera independiente:** rama `archive/softmobile-repairs-paused-20261107`. Esta rama activa/PR **no debe introducir tablas, rutas, modelos, interfaces ni servicios de reparaciones**.

## Flujo que está ejecutándose en el VPS
`softmobile-openclaw-supervisor.service` → `softmobile-openclaw-director.service` → `softmobile-pilot-executor.service` → `softmobile-finance-audit.service` → `softmobile-event-router.service` → `softmobile-release-gate.service`.

Arranque automático desde el timer del supervisor cada 30 minutos. Los cinco sucesores se inician solo cuando la etapa anterior termina correctamente. **Se quitó la etapa repair-workflow-lab del flujo de OnSuccess.** La ejecución manual histórica del laboratorio de reparaciones no concede permisos ni implica integración al negocio.

El archivo `DIRECTOR.json` debe tener `scope=sales_only`. El ejecutor rechaza tareas ajenas a la lista comercial, el router oculta las antiguas tareas de reparaciones y el certificado `CERTIFICATION.json` debe tener `scope=sales_only`. Todas las operaciones son de solo lectura o propuestas internas; no se pueden enviar respuestas, campañas, pagos, compras ni cambiar stock. La autorización pública sigue `false`.

## Áreas activas de ventas
- **Vendedor IA:** simulación de cotización, objeciones, cierre, uso correcto de descuentos y verificación de precio/stock antes de prometer al cliente. No asumir que una venta simulada es real.
- **Catálogo y fotografías comerciales:** detectar modelos activos sin inventario y solicitudes antiguas de fotos, sin contactar clientes.
- **Seguimientos comerciales:** propuestas internas únicamente, siempre sujetas a consentimiento, ventana permitida y revisión humana.
- **Márgenes/finanzas de ventas:** SQL `BEGIN TRANSACTION READ ONLY` con totales agregados; pedidos pendientes no equivalen a ventas. Distinguir diferencias potenciales de tarjeta/financiamiento de anomalías a conciliar, sin atribuir pérdidas.
- **Publicidad para vender celulares:** datos Metricool de importación manual insuficientes para probar campañas actuales y atribución de ventas; no cambiar presupuestos automáticamente.
- **Calidad y código del vendedor:** 72 simulaciones comerciales ficticias, replays QA sintéticos, fuente Ruby fijada por SHA y revisión de código en borrador sin autopromoción.

## Validación
El 7 de noviembre (HN) se ejecutó la cadena de seis servicios con `Result=success`, **192/192** pruebas unitarias aprobadas, **8 tareas comerciales** del director, **0 tareas activas de reparaciones**, **0 fallos** y **0 mensajes públicos**. El certificado comercial previo a WhatsApp marca **4/9** condiciones; no está listo para lanzamiento.

Las filas de ventas en la base no están conciliadas: 458 órdenes pendientes, 0 completadas y 0 cierres. Las anomalías de precios/totales son alertas que necesitan verificación, no pérdidas demostradas.

## Seguridad y próximos pasos
No desplegar, fusionar, habilitar WhatsApp o pagos sin autorización. Revisar pruebas y reglas del vendedor, integrar precios reales e inventario autorizado con controles contra promesas falsas, mejorar cierres offline, validar atribución de anuncios y convergencia independiente. Si falta evidencia, bloquear el resultado.

Las unidades existentes para reparaciones no están en la cadena automática y los archivos de desarrollo se conservaron solo en la rama archivada. **Este PR debe continuar EN BORRADOR.**


## Actualización 8 noviembre 2026 — calidad comercial comprobada
- `DIRECTOR.json.seller_reply_quality` distingue la respuesta textual REAL del Ruby vigente de un checkout inventado por el laboratorio. **Ruby actual: 36/72** conversaciones válidas; **candidato SIN DESPLEGAR: 72/72** en los mismos 72 casos de prueba ficticios.
- Fallas del Ruby actual identificadas: el vendedor repregunta ciudad ya indicada, reinicia la conversación al aceptar una negociación y olvida la reserva para mañana. Se creó un parche exclusivamente comercial de 51 líneas, fijado al SHA-256 de origen; refuerza también el tono natural de respuestas sobre precio/stock sin confirmar importes.
- Regresiones: **21 pruebas unitarias comerciales y 72 pruebas anteriores** aprobadas contra el candidato; cero llamadas API, envíos, pagos, movimientos de inventario o cambios al vendedor público. El parche recreado en una copia desechable coincide por bytes con el candidato.
- `softmobile-seller-conversation-quality.timer` ejecuta el análisis de respuestas del Ruby ACTUAL cada 4 horas, sin red hacia clientes. El director emite `ventas_calidad_conversacional` como una tarea `awaiting_qa`, sin detener las etapas por defectos comerciales ya conocidos.
- **192 pruebas del supervisor aprobadas**. `CERTIFICATION.json.scope=sales_only` informa **4/9** condiciones satisfechas; nueva condición: aprobación de calidad del vendedor Ruby vigente, actualmente bloqueada.
- Para detalles técnicos y comparación, ver `sales-quality/README.md` y `sales-quality/sales-bot-v2-reply-candidate.patch`. La IA actual sigue sin recibir este cambio; WhatsApp sigue aplazado. La mejora del candidato no autoriza despliegue sin revisión humana independiente.


### QA independiente por frases nuevas — 8 nov 2026
Se ampliaron los casos fijos con **18 reexpresiones nuevas** de negociación, reservas y envíos. Ruby activo **6/18**; candidata inicial **8/18**; candidata generalizada **18/18**, manteniendo **72/72** en ambos grupos originales. Se detectó y corrigió el sobreajuste antes de recomendar integrar el cambio. 21 tests comerciales unitarios y 192 del supervisor siguen aprobados. Se conserva la versión activa sin cambios, y `SALES_CANDIDATE_QA.json` identifica a la candidata como **no desplegada**. Todavía falta validación independiente en otras condiciones y con el vendedor IA antes de autorizar uso público.


## 8 noviembre 2026 — ejecutor de correcciones comerciales en automático

### Lo que cambió en el VPS
- Se creó **`sales_autofix_loop.py`**, un ciclo autónomo y programado de **búsqueda, revisión de fuente SHA, creación de variante, simulación, detección de errores, selección de una regla correctiva autorizada, reintento y staging privado**. No se instala ni reemplaza el Ruby comercial.
- Unidad `softmobile-sales-autofix-lab.service` con timer activo cada **seis horas**. Las llamadas al motor Ruby se realizan en Docker efímero `--network none`, solo lectura y con recursos limitados. El reporte `quality/autonomous-sales/latest.json` es auditable.
- `sales_rotating_challenges.py` alterna **seis pruebas adicionales por día**, separadas del conjunto inicial de 72 y las 18 reformulaciones. Se validó ambos días de rotación y el bloqueo seguro si ninguna regla sirve.
- Una ejecución automática demostrada: intento 1 **4/6** en preguntas rotativas, con fallas de apartados; el algoritmo eligió `reserve_synonyms` de su lista revisada, construyó otro candidato y repitió. Intento 2 **6/6**, más **72/72** de calidad conversacional, **18/18** reformulaciones, **72/72** del checkout ficticio y **21 tests**. **0 comunicaciones, 0 pagos, 0 cambios a inventario o Ruby público**.
- Se añadieron **24 pruebas** del ejecutor y la interfaz de generación de preguntas Groq, incluyendo límite de cuota, fuente pinneada, fallo cerrado y reintentos. El supervisor general pasó **195/195** pruebas.
- `sales_ai_challenges.py` está programado **1 solicitud Groq/día como máximo** para generar únicamente preguntas ficticias, no código. La primera llamada devolvió `ai_challenge_provider_or_schema_blocked`; la cuota quedó reservada y los reintentos quedaron bloqueados por ese día. **Esta fuente de generación IA todavía no está validada**, por lo que el sistema se apoya en las preguntas rotativas locales.
- El director OpenClaw incluye `autonomous_sales` en `DIRECTOR.json` y emite la tarea `ventas_autofix_review` con estado `awaiting_qa` en el ejecutor. La certificación de trabajo no WhatsApp alcanza **5 de 10 requisitos**, conservando `public_release_permitted=false`.

### Límite de autonomía actual
**Está operativo el ciclo completo de corrección automática dentro de reglas revisadas y aisladas.** Aún **no** es un programador genérico de IA capaz de cambiar arbitrariamente cualquier archivo ni de fusionar o desplegar código. No hace pruebas con clientes reales y no confirma ventas ni retorno real. El generador viejo `softmobile-patch-proposer.timer` sigue **deshabilitado** (desalineado con el Ruby actual). Los cambios creados esperan revisión de seguridad independiente y aprobación del propietario.

Las reparaciones están archivadas; WhatsApp, envíos reales, cobros, descuentos reales, campañas y despliegues permanecen fuera de alcance.


### Estado persistente de automejora del vendedor
Desde la segunda ejecución el agente conserva y revalida el mejor candidato SHA-pinneado en vez de reescribir el mismo parche cada seis horas. Los resultados pasan a un historial acotado de 120 ciclos sin datos de clientes. Verificación: ejecución reanudada con **1 intento**, 72/72+18/18+6/6+72/72 y 21 regresiones unitarias, 0 despliegues; `auto_corrected_ever=true`. El director verifica el SHA del artefacto, mantiene la tarea `ventas_autofix_review` pendiente de QA y conserva el indicador **5/10**. El proveedor externo Groq aún no consiguió generar un lote de pruebas válido; el banco local diario continúa funcionando sin él.


### 8 de noviembre, Honduras — refuerzo adversarial de ventas
Se ejecutaron **11 conversaciones nuevas de compra** fuera de las 72+18+6: el Ruby activo superó **5/11**; la candidata **11/11**. Se corrigieron reservas coloquiales («apartármelo para el viernes»), reconocimiento de cancelación del interés, costo y ETA de envío con ciudad previamente indicada y respuesta a supuestas aprobaciones bancarias sin verificarlas.

Estas pruebas forman ahora una **condición obligatoria del ejecutor autónomo**: ningún parche llega a `qa_passed_review_required` sin **72/72 + 18/18 + 6/6 + 11/11**, las 72 regresiones de checkout ficticio y las pruebas unitarias. Se incorporó un identificador de revisión de reglas para que al cambiar la lógica **no se reutilice un candidato anterior solo por tener un buen resultado en una versión vieja**.

La ejecución actual del ejecutor programado pasó tras detectar fallas de reserva en el primer intento y elegir una corrección acotada para aprobar en el segundo. Luego reanudó su candidato con una segunda ejecución de comprobación, sin tocar el bot activo. **56 pruebas del laboratorio y 195 del supervisor** aprobadas, 0 mensajes, 0 cambios de inventario, 0 ingresos reales verificados, 0 despliegues. Certificado comercial **5/10**, público bloqueado.


### 8 nov 2026 — Catálogo auditado exclusivamente para ventas
Se añadió `sales_catalog_audit.py` con consultas PostgreSQL `BEGIN TRANSACTION READ ONLY`, sin extraer nombres/SKU/IMEI, precio unitario, datos personales ni registros de clientes. El servicio `softmobile-sales-catalog-audit.timer` se ejecuta cada 4 horas en el VPS con red externa bloqueada.

**Inventario ERP agregado observado:** 189 productos activos, 54 con stock positivo en ubicaciones activas, 53 con modelo/color/capacidad/precio HNL completos, 135 activos sin stock, 1 unidad con stock sin todos los datos necesarios para cotizar y 3 productos activos cuyo precio registrado está por debajo del costo. **Estos números no autorizan cotizar**: el ERP no demuestra vigencia de precios ni stock real de los aliados. Las tres diferencias requieren revisar promociones, costos y condiciones; no son pérdidas confirmadas.

El director OpenClaw incluye `sales_catalog` en `DIRECTOR.json`, crea `ventas_catalogo_calidad` para revisión humana y el ejecutor lo procesa sin modificar productos, precios ni pagos. Última cadena verificada: **11 tareas comerciales**, cero fallas, cero mensajes públicos, certificado **5/10** (sin WhatsApp), lanzamiento bloqueado. **207 pruebas unitarias del supervisor**, más **56 del laboratorio comercial**.
