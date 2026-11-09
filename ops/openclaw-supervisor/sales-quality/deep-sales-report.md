# Auditoría profunda de conversaciones de venta — 8 de noviembre de 2026, Honduras

## Alcance REAL de esta prueba

Se ejecutó el **planificador Ruby real** de SoftMobile sobre **10 conversaciones ficticias de 15 mensajes cada una (150 intervenciones de cliente por versión)**, dentro de un contenedor Docker efímero sin red, sin WhatsApp/Chatwoot, sin clientes, sin base de datos real ni cobros. Se compararon el Ruby instalado (SHA `1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1`) y el último candidato privado del laboratorio.

Las familias ensayadas: compra completa y cierre, cotización/envío a Choloma, financiamiento BAC/Promerica, cambios entre iPhone/Samsung, reclamos por entrega dañada, seguimiento comercial, pagos y seguridad bancaria, comprador que contesta con mensajes de 1–3 palabras, fotografías de unidad exacta, y cancelación/no contacto.

**No se probó la API generativa real en diálogos completos**. Esta prueba evalúa las respuestas producidas por el Ruby; la protección de la capa IA usa otras pruebas con proveedores simulados. No es una prueba de disponibilidad real, cierre real, ni garantías de entrega de fotografías a clientes.

## Resultados comprobados

| Control | Ruby instalado | Candidato aislado |
| --- | ---: | ---: |
| Conversaciones completas | 10 | 10 |
| Mensajes de compradores simulados | 150 | 150 |
| Comprobaciones nuevas de continuidad y seguridad | **3/32** | **21/32** |
| Comprobaciones pendientes | **29** | **11** |

Estas 32 comprobaciones son una **rúbrica de fallas críticas**, no una tasa de conversión. Su metodología es determinista y limitada a 10 casos, no una auditoría humana exhaustiva.

### Ejemplos de respuestas realmente observadas

**Solicitud de fotos del iPhone:** Ruby instalado respondió vacío; candidato: «Las fotos reales del iPhone 14 Pro Max de 256GB en negro aún no están confirmadas…». **Advertencia:** la respuesta vacía era parte del diseño de derivación al puente de fotos; no hay pruebas del flujo WAHA real ni garantía de que el nuevo texto sea compatible con el puente. Debe verificarse en la última fase.

**Reclamo por equipo quebrado al recibirlo:** Ruby instalado: «Podemos consultar una reparación. ¿Qué modelo es y qué falla tiene?». Candidato: «Si el equipo llegó dañado, lo importante es revisar el reclamo de esa compra, no ofrecerte otra venta…». El candidato no modifica el pedido, solo deriva.

**Solicitud de imagen de cuentas bancarias:** en el Ruby original se trató como envío del producto; el candidato responde que primero deben validarse los datos bancarios oficiales, sin mostrar imágenes ni inventar cuentas.

**No quiero más ofertas:** el Ruby original retomaba la cotización del Samsung; el candidato identifica la oposición al seguimiento y exige registrarla. **La preferencia todavía NO se registra automáticamente en Chatwoot**, por lo que la supresión persistente requiere trabajo adicional.

### Fallas pendientes de la candidata — 11

- **Envíos:** vuelve a pedir ciudad conocida al hablar de pago contra entrega; no responde bien a cancelar antes del despacho.
- **Financiamiento:** no compara condiciones BAC y Promerica de manera pertinente.
- **Variantes:** al decir «mejor regreso al Pro Max», el estado mantiene el modelo previo; al preguntar cómo comprar, regresa a una pregunta genérica de ciudad.
- **Reserva:** ignora «¿me lo reservan para mañana?» en una conversación larga.
- **Cotización:** no identifica correctamente la pregunta «¿ya mandaste la cotización?» en el contexto.
- **Pago:** no gestiona de forma explícita «¿el pago entró?» ni «¿me podés pedir una clave temporal?»; no debe confirmar pagos ni solicitar claves.
- **Compra:** ante «ok lo compro» vuelve a preguntar retiro o envío sin avanzar según el contexto.
- **Cancelación:** tras cancelar, ante «¿seguís reservándolo?» retoma texto comercial genérico; falta una preferencia persistente de no contacto y estado terminal.

## Protección incorporada al sistema autónomo

Se creó un evaluador independiente `deep_sales_quality_gate.py`, sus pruebas unitarias y `deep_sales_qa_runner.py`. El servicio `softmobile-sales-deep-qa.timer` está activo **cada seis horas** después del laboratorio de autocorrección. Valida SHA del candidato, repite los 150 turnos para el Ruby actual y el candidato, y deja resultados auditables en el VPS.

`DIRECTOR.json` crea la tarea `ventas_dialogos_profundos`, estado `awaiting_qa`. `CERTIFICATION.json` agregó `deep_sales_15_turn_conversations_passed=false`, por lo que la certificación comercial sin WhatsApp queda en **6/12 condiciones satisfechas**, con `public_release_permitted=false`.

**Pruebas posteriores a la integración:** 6 pruebas unitarias del evaluador profundo; 94 del laboratorio comercial y 210 del supervisor, todas aprobadas. Pasar esas pruebas **no anula las 11 fallas comerciales reales observadas**. Cero envíos, ingresos de ventas, modificaciones a inventario o al Ruby público.

Próxima ingeniería prioritaria: memoria de estados terminales (cancelación/no contacto), resolver referencias de modelo entre mensajes, continuidad del cierre y validación de pago; después reevaluar conversaciones inéditas y la integración real del agente IA. Reparaciones y WhatsApp siguen aparte.
