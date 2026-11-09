# Plan de ejecución — ventas de celulares SoftMobile

**Objetivo vigente:** convertir a OpenClaw en un sistema de mejora y supervisión del vendedor IA de celulares. **No trabajar en reparaciones, productividad del taller o WhatsApp** antes de nueva instrucción del propietario. Copia de reparaciones archivada en `archive/softmobile-repairs-paused-20261107`.

## Fase 1 — Coordinación y alcance comercial: VERIFICADA
- Director restringido a `scope=sales_only`, 8 tareas comerciales activas en última ejecución.
- Ejecutador rechaza tareas fuera de ventas, inventario disponible, fotos de cotización, QA, márgenes, publicidad o cambios de código del vendedor.
- Ruta systemd automática: supervisor → director → ejecutor → auditoría financiera comercial → eventos → certificado.
- Almacén histórico de eventos preservado sin exponer reparaciones como tareas activas. 192/192 pruebas, 0 envíos públicos.

## Fase 2 — Calidad del vendedor y cierre: EN PROGRESO
- 72 conversaciones comerciales completamente ficticias con el Ruby piloto vigente; pruebas de objeciones, daños de pedidos, seguridad y cancelación.
- Comprobar precio, modelo, color, memoria, disponibilidad, garantías, regalos, promociones, financiación, descuentos y lenguaje natural.
- Mejorar criterios por escenarios, tests de regresión, conversaciones completas, tasa de éxito en simulación; ninguna prueba equivale a ventas reales.

## Fase 3 — Catálogo comercial y márgenes: EN PROGRESO
- Auditar stock, fotos y costos sin realizar compras ni cambios de inventario.
- 458 órdenes pendientes y cero cierres son registros sin ingresos verificados.
- Investigar diferencias por método de pago y productos activos bajo costo, distinguiendo cargos de tarjeta/financiamiento de pérdidas reales.

## Fase 4 — Seguimientos y publicidad: PENDIENTE
- Definir seguimiento comercial con consentimiento comprobable; solo simulación y propuestas internas hasta última fase WhatsApp.
- Revalidar fuente de campañas Meta; los datos actuales de Metricool no acreditan gasto ni retorno reales. Sin ajustes automáticos de presupuesto.

## Fase 5 — Mejora autónoma segura del vendedor: PARCIAL
- Guard de SHA Ruby vigente; el generador antiguo sigue bloqueado por incompatibilidad de fuente.
- Todo cambio requiere propuesta acotada, revisión independiente, regresiones, comparación antes/después, evaluación de costo/API y autorización para integrar.
- Control de gastos en VPS y límites de OpenClaw.

## Fase 6 — Canal WhatsApp real y lanzamiento: APLAZADA POR DECISIÓN DEL PROPIETARIO
No reiniciar WAHA, no habilitar servicio público, no enviar contactos, no alterar el canal. Solo después de que las fases comerciales anteriores cuenten con evidencia y autorización explícita.

**Indicador activo, no WhatsApp: 4/9 condiciones.** No afirmar 100% ni rentabilidad demostrada hasta pruebas independientes con datos reales conciliados.


## Iteración actual del vendedor comercial (8 nov 2026)
- **Falla detectada al medir texto de ventas:** las 72 pruebas originales eran de variantes y checkout exclusivamente ficticio, no demostraban respuestas comerciales satisfactorias. Nueva evaluación del Ruby activo: **36/72**, con 36 errores concentrados en negociación, reserva y envío.
- **Parche en rama, sin despliegue:** mismo set de 72 conversaciones pasa **72/72** con el candidato y 72/72 pruebas originales; otras 21 pruebas unitarias cubren estado de compra, reintentos de reserva, retención del destino, pagos no confirmados y cancelación.
- **Monitoreo instalado:** evaluación offline del Ruby actual cada 4 horas, reporte saneado en DIRECTOR/SALES_CANDIDATE_QA y tarea prioritaria `ventas_calidad_conversacional`; 192 regresiones del supervisor aprobadas.
- **Nuevo marcador comercial:** 4/9 requisitos de prelanzamiento. El candidato es una hipótesis probada con casos sintéticos, no una versión productiva ni aprobación real.
- **Siguiente paso técnico antes de plantear cambios públicos:** auditoría independiente de respuestas generadas y pruebas con otros giros conversacionales, cotizaciones de stock/precio verificado, integración segura con IA y salida pública solo después de nueva autorización. No tocar reparaciones ni WAHA.


### Nuevo hito de pruebas sin producción — 8 nov
- El conjunto original de 72 casos no bastaba para confiar en la mejora: en 18 frases inéditas la primera candidata solo superó 8.
- Se corrigieron reglas de negociación en lenguaje natural, reservas para días de la semana y plazos/costos de envío con destino previamente indicado.
- Última candidata: **72/72 escenarios iniciales + 18/18 nuevos + 72/72 regresiones heredadas**, y **21 pruebas unitarias** aprobadas; no son ventas ni mensajes reales.
- Pendiente: evaluación independiente fuera de los conjuntos conocidos, prueba de integración con IA real de manera aislada y revisión de código del PR; no autorizar despliegue ni WhatsApp.
