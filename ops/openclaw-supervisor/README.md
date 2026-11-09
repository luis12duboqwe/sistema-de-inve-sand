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
