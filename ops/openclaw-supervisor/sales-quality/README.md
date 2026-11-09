# QA comercial del vendedor IA — laboratorio aislado

**Objetivo:** evaluar si el vendedor SoftMobile mantiene una conversación útil de venta, sin confundir una operación ficticia del simulador con una venta o un cierre comercial real.

## Hallazgo reproducible
El laboratorio existente `conversion_training_lab.py` aprobaba **72/72** escenarios: exactitud de modelo/capacidad/color, una operación de apartado/checkout en inventario completamente ficticio y ausencia de promesas comerciales detectadas.

La nueva herramienta independiente `sales_conversation_quality.py` inspecciona **las respuestas textuales del motor Ruby real** (no los comprobantes ficticios), sin red ni acceso a clientes. Misma selección fija de 72 conversaciones: **36/72** pasan, **36/72** no cumplen los nuevos criterios de continuidad.

| Familia | Ruby actual | Candidato |
|---|---:|---:|
| Compra y retiro | 12/12 | 12/12 |
| Financiamiento | 12/12 | 12/12 |
| Negociación | 0/12 | 12/12 |
| Reserva | 0/12 | 12/12 |
| Envíos | 0/12 | 12/12 |
| Accesorios/garantía | 12/12 | 12/12 |
| **Total** | **36/72** | **72/72** |

Fallos concretos:
- Se repetía la pregunta de la ciudad cuando el cliente ya había dicho Choloma.
- Ante «si es posible sigo con la compra», el sistema regresaba al saludo/ubicación.
- Ante «reservarlo para mañana», el sistema ignoraba la fecha solicitada.

## Cambio propuesto, sin desplegar
`build_sales_followup_candidate.py` exige que la fuente Ruby original tenga SHA-256 exacto `1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1` y una única ancla revisada. Genera un candidato y el parche `sales-bot-v2-reply-candidate.patch` sin escribir el archivo Ruby público. La nueva lógica mejora respuestas de negociación condicionada, apartados sin aprobación, costos y plazos de envío; nunca ofrece cuota, descuento, precio, reserva, pago, fecha o existencias como hechos sin fuente autorizada.

Se reejecutaron las 72 pruebas originales del candidato: **72/72**, cero promesas no verificadas detectadas, nueve checkouts *ficticios*, cero mensajes/cobros/inventario reales. La batería de pruebas adicionales `test_sales_conversation_quality.py` junto con el test comercial anterior pasó **21/21**. La nueva evaluación del candidato también marcó **72/72**.

**Límite fundamental:** la rúbrica es determinista y cubre solo los casos creados, no comprueba de manera independiente que el vendedor funcione con todos los clientes; tampoco demuestra resultados con IA externa o transporte WhatsApp. El candidato requiere nuevas pruebas independientes y revisión de código antes de integrarse al bot.

## Control en el VPS
Unidad `softmobile-seller-conversation-quality.service` cada cuatro horas por su timer, solo lectura del Ruby original y resultados agregados en `quality/seller-conversation-baseline.json`. Informa SHA y recuentos. No consume tokens de API. OpenClaw consume esos recuentos en `DIRECTOR.json.seller_reply_quality` y crea `ventas_calidad_conversacional` como tarea prioritaria en `awaiting_qa`, sin cortar la cadena por una falla de la rúbrica.

La certificación comercial declara `ruby_sales_conversation_quality_passed=false` y presenta **4/9 condiciones satisfechas**. Toda salida pública sigue prohibida.

**Pendiente:** revisión de variantes adversariales y de la seguridad contra promesas, continuidad de cambios de modelo, aprobación de la candidata y pruebas en aislamiento con el agente IA. WhatsApp, desplegar el bot, clientes y pagos permanecen fuera del alcance.


## Pruebas de generalización (8 nov 2026)
Se creó `sales_heldout_challenges.py` como una segunda batería de **18 formulaciones distintas** que no pertenecían al conjunto fijo de 72. Las pruebas incluyen negociación coloquial («Si se puede, seguimos»), reservas en días de la semana («¿Me lo apartás para el lunes?») y envíos con una ciudad indicada en un mensaje anterior («¿En cuánto tiempo llega?»).

- Ruby original: **6/18**.
- Primera revisión del candidato: **8/18**. Esto reveló sobreajuste al conjunto de 72.
- Candidato generalizado: **18/18**, conservando **72/72** en la evaluación inicial y **72/72** en las pruebas heredadas del checkout simulado.
- **21 tests unitarios** de guardas comerciales aprobados. El parche final contiene 55 líneas, se aplica sin errores a la fuente fijada por SHA y produce exactamente los mismos bytes que el candidato.

Este resultado no equivale a una prueba estadística completa ni a conversaciones reales. No se ha activado el bot, ni enviado mensajes, cobrado, reservado o alterado inventario. `SALES_CANDIDATE_QA.json` es la evidencia interna que consumen los especialistas de OpenClaw; el candidato conserva `deployment_authorized=false`.

La versión real continúa **36/72 y 6/18** hasta que se autorice una sustitución después de QA independiente.


## Automatización del propio laboratorio (8 nov 2026)
Además de los resultados anteriores, hay un ejecutor `sales_autofix_loop.py` que **no requiere que ChatGPT esté abierto**: se inicia por systemd cada seis horas. Usa únicamente parches y términos comerciales revisados, fuente Ruby fijada por SHA y Docker efímero sin red. Evalúa 72 conversaciones, 18 reformulaciones y 6 giros rotativos nuevos; si falla un caso, escoge una receta segura según la familia del error, vuelve a generar y repetir todas las pruebas, con límite de 4 iteraciones. Todo candidato queda solo como parche de revisión.

**Ejecución comprobada:** 4/6 pruebas rotativas en el primer intento, 6/6 en el segundo, junto a 72/72, 18/18, 72/72 y 21 unitarios. Reportes disponibles en `autonomous-sales-latest.json` y `autonomous-reviewed-candidate.patch` del PR.

Se configuró un generador Groq de *datos de prueba* con tope de una solicitud al día; su primera solicitud no generó un lote válido, por lo que **no debe presentarse como generación autónoma de parches IA verificada**. El laboratorio rotativo funciona sin ese proveedor. La autonomía está circunscrita a recetas validadas, nunca a despliegue arbitrario, actualizaciones públicas o clientes reales.


### Continuidad automática entre ejecuciones (9 nov UTC)
Se añadió persistencia verificable del mejor candidato: el servicio consulta `quality/autonomous-sales/latest.json`, comprueba que el candidato sigue vinculado al SHA actual del vendedor, lee únicamente su archivo privado y valida la firma SHA y los límites del parche. Si todo coincide, **reanuda desde el último candidato**, en vez de comenzar cada seis horas con la misma corrección. Las reglas ya aplicadas no vuelven a aplicarse. Un archivo manipulado bloquea la ejecución.

Prueba: ciclo inicial 2 intentos, de 4/6 a 6/6; en un nuevo ciclo el servicio **reanudó el mismo candidato, lo revalidó en un intento, mantuvo `auto_corrected_ever=true` y guardó historial** en `quality/autonomous-sales/history.json`. **25 pruebas unitarias específicas** de controles de autonomía (incluido esquema Groq) aprobadas; **195** del supervisor. La fuente Ruby pública conserva su SHA. `DIRECTOR.autonomous_sales.autonomous_failure_corrected` queda en true y el certificado sigue en **5/10** con `public_release_permitted=false`.


## Tercer lote — once casos adversariales nuevos
El archivo `sales_adversarial_quality.py` evalúa otras **11 conversaciones completas, distintas de los 72 principales y 18/6 giros adicionales**. Incluye reservas coloquiales, envío con destino ya indicado, costo de mensajería confundido con precio del teléfono, cancelación, transferencia que no acredita pago, consultas de crédito aprobado y cambio de capacidad/color. Se obtuvieron **5/11 para el vendedor activo**, **11/11 para la candidata** con las correcciones acotadas. Ver `adversarial-baseline-11.json` y `adversarial-candidate-11.json`.

En el flujo autónomo, `sales_autofix_loop.py` ahora exige 11/11 adicionales antes de marcar la revisión como apta para QA. Sigue fallando de forma segura si los datos, el origen SHA o el banco de pruebas no son válidos. Tras la última ejecución autónoma, la candidata superó 72+18+6+11 y 72 regresiones antiguas, así como **30 pruebas unitarias de la candidata**. **No son ventas reales.** La cadena del supervisor pasó **195 pruebas**, su certificación continúa **5/10** y ningún bot público se modificó.

Para Groq se simplificó el JSON Schema del proveedor, pero el validador local mantiene longitud, seguridad, distribución y datos ficticios. El proveedor no ha producido todavía las seis conversaciones válidas en vivo; el banco local sigue siendo el respaldo probado.


## Validación de catálogo para vender sin inventar precios
La ejecución `sales_catalog_audit.py` resume solo números del ERP (fuente interna, no atribución al aliado): 189 productos activos, 54 con existencias positivas en sucursales activas, 53 con precio y combinación modelo/color/capacidad registrada y tres entradas con precio inferior a costo. Revisión automática cada cuatro horas; reporte `catalog-audit-aggregate-snapshot.json`, sin detalles de productos, códigos, precios individuales, cuentas o clientes.

El agente **no puede** convertir este registro en una promesa de unidad o cotización real. Falta validar cuándo se actualizó el precio/stock y de qué aliado proviene; estas comprobaciones solo habilitan revisión de calidad de datos. Los nuevos controles de catalogación pasan 9 pruebas; el supervisor completo alcanza 207.


## Cortafuegos del agente conversacional de ventas
Además de la calidad del Ruby, se corrigió el desvío de datos de `sales_ai_agent.py`: la función `approved_reply` opera sobre `knowledge/catalogo.json`, que contiene precios históricos y reglas no necesariamente vigentes. La ruta `reference_only` puede usarlo para orientación interna de diálogo, **pero ninguna cifra, porcentaje, regalía, aprobación, garantía o mensaje enviado se considera verificado por ese origen**.

`reference_commerce_safe` valida la salida incluso cuando proviene de una plantilla considerada aprobada; `safe_reference_sales_reply` ofrece respuestas comerciales naturales sin afirmaciones sin evidencia y conserva la variante seleccionada. **También actúa cuando la API falla.** `test_reference_commerce_firewall.py` usa el catálogo histórico y un proveedor LLM simulado para demostrar que una cotización antigua (por ejemplo L 16,700) ya no llega a la respuesta del agente en modo referencia. No toca `approved_commerce.py` ni el bot público.

La batería focalizada superó **94/94** pruebas, incluidas 38 del agente y referencia. El autocorrector de cada seis horas ejecutó **68/68** pruebas de candidatura y OpenClaw **207/207**, con `reference_only_agent_firewall_verified=true`, tareas pendientes de QA y certificado **6/11**. No hubo contactos, cobros, órdenes, modificación de inventario ni despliegue.
