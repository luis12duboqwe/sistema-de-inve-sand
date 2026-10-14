# Índice provisional de hallazgos

No es informe final ni autoriza correcciones. Confirmados por código, reproducciones lógicas aisladas y riesgos de prueba se distinguen en cada bloque. Posibles relaciones entre IDs conservan trazabilidad; contar entradas no equivale a causas raíz independientes.

| ID | Gravedad | Hallazgo | Evidencia completa |
|---|---|---|---|
| BUS-01 | HIGH | Finalizar/cancelar/editar venta consume reserva ajena del mismo producto | BLOQUE_business.json |
| BUS-02 | HIGH | Recepción cero traslada todos IMEIs sin mover stock | BLOQUE_business.json |
| BUS-03 | HIGH | Garantía permite IMEI de otro producto de la misma orden | BLOQUE_business.json |
| BUS-04 | MEDIUM | Garantía serializada se cierra sin entregar reemplazo | BLOQUE_business.json |
| BUS-05 | HIGH | Retoma sobrescribe IMEI vendido/reservado/de otra sede | BLOQUE_business.json |
| BUS-06 | HIGH | Órdenes autorizadas exponen stock y seriales de sedes ajenas | BLOQUE_business.json |
| BUS-07 | HIGH | POST crear negocios sin clave idempotente duplica efectos al reintentar | BLOQUE_business.json |
| BUS-08 | MEDIUM | Ajuste no serializado tiene dos commits y lectura de stock sin lock | BLOQUE_business.json |
| BUS-09 | MEDIUM | Valor de inventario suma costos/precios USD y HNL sin convertir | BLOQUE_business.json |
| BUS-10 | MEDIUM | Venta commit antes de auditoría permite transacción durable sin audit y respuesta 500 | BLOQUE_business.json |
| OPS-01 | HIGH | Backup automático Compose escribe fuera del volumen persistente | BLOQUE_deploy.json |
| OPS-02 | HIGH | Healthcheck operativo exige una ruta que nginx bloquea | BLOQUE_deploy.json |
| OPS-03 | HIGH | Backup VPS anuncia éxito aunque pg_dump falle | BLOQUE_deploy.json |
| OPS-04 | HIGH | Migración monetaria SQLite bloquea arranque por parámetros Decimal | BLOQUE_deploy.json |
| OPS-05 | HIGH | Bootstrap VPS nuevo no genera SETUP_TOKEN obligatorio | BLOQUE_deploy.json |
| OPS-06 | HIGH | Ruta env relativa recomendada se invalida al cambiar directorio en release | BLOQUE_deploy.json |
| OPS-07 | HIGH | Restore no reemplaza BD existente y no es atómico | BLOQUE_deploy.json |
| OPS-08 | HIGH | --truncate migra después de confirmar truncado en transacción separada | BLOQUE_deploy.json |
| OPS-09 | MEDIUM | Utilidad demo de credenciales elimina otras configuraciones del perfil | BLOQUE_deploy.json |
| FE-01 | HIGH | Pagos mixtos con tarjeta calculan/importan totales incompatibles con backend | BLOQUE_frontend.json |
| FE-02 | HIGH | Reintentos automáticos repiten mutaciones no idempotentes | BLOQUE_frontend.json |
| FE-03 | MEDIUM | Venta rechazada cierra y borra el formulario como si hubiese terminado | BLOQUE_frontend.json |
| FE-04 | HIGH | Traslado multi-modelo anunciado como una operación deja resultado parcial y repetir duplica líneas | BLOQUE_frontend.json |
| FE-05 | HIGH | Caché global de negocio permite mezclar datos de usuarios/ubicaciones entre sesiones y pestañas | BLOQUE_frontend.json |
| FE-06 | MEDIUM | Lista transferencias corta silenciosamente a la primera página de50 | BLOQUE_frontend.json |
| FE-07 | MEDIUM | Notas API desaparecen de tarjeta y editor por notes/notas | BLOQUE_frontend.json |
| FE-08 | MEDIUM | Reparación automática sigue escribiendo stock local en producción y anuncia corrección | BLOQUE_frontend.json |
| FE-09 | MEDIUM | Accesorios serializados no tienen selección/validación IMEI en edición y garantía | BLOQUE_frontend.json |
| FE-10 | MEDIUM | Enviar fotos permite múltiples clics concurrentes; selección archivos comparte estado entre clientes | BLOQUE_frontend.json |
| FE-11 | LOW | Hook WebSocket reconecta tras disconnect/cleanup usando token antiguo | BLOQUE_frontend.json |
| SEC-AI-001 | HIGH | JWT sin permiso IA accede a conversaciones e inventario global | BLOQUE_security-ai.json |
| SEC-AI-002 | HIGH | Creación de ventas por IA omite orders:create | BLOQUE_security-ai.json |
| SEC-AI-003 | HIGH | Respuesta duplicada puede pertenecer a otro cliente | BLOQUE_security-ai.json |
| SEC-AI-004 | HIGH | Pronóstico rápido evade restricción por ubicación | BLOQUE_security-ai.json |
| CH-001 | HIGH | Corrección de webhook no cubre idempotencia del endpoint IA ni limpieza compartida | BLOQUE_security-ai.json |
| CH-005 | MEDIUM | n8n sigue con contrato training inválido y sin entrega Meta | BLOQUE_security-ai.json |
| CH-006 | MEDIUM | Clave deduplicación global sin cuenta/canal/cliente | BLOQUE_security-ai.json |
| PHOTO-001 | MEDIUM | Fotos ignoran canal de origen persistido | BLOQUE_security-ai.json |
| PHOTO-002 | MEDIUM | Envío de lote de fotos no es reintentable sin duplicados | BLOQUE_security-ai.json |
| AN-001 | MEDIUM | Analytics y forecast usan fecha creación en lugar de fecha venta | BLOQUE_security-ai.json |
| AN-002 | MEDIUM | Cache forecast ignora parámetros y caducidad | BLOQUE_security-ai.json |
| AUTH-001 | MEDIUM | Cambiar contraseña no invalida JWT anterior | BLOQUE_security-ai.json |
| T01 | MEDIUM | El único E2E PostgreSQL acepta competidor 500/503 como éxito de control de concurrencia; no comprueba ausencia de orden, items, pagos o ledger parcial del perdedor. | BLOQUE_tests.json |
| T02 | MEDIUM | NewOrderDialog solo comprueba nombre vacío; tests de App son inspección textual y no ejecutan App. No verifican venta real serializada, pagos múltiples, financiamiento, selección localización, error/reintento ni estados UI al fallar API. | BLOQUE_tests.json |
| T03 | MEDIUM | Suite de migración SQLite->PostgreSQL utiliza SQLite como target en todos los casos; no verifica conversión PG, secuencias, constraints ni rollback de migración completa. | BLOQUE_tests.json |
| T04 | MEDIUM | test_transfer_reservation_blocks_concurrent_order usa barrier.wait y join sin timeout; workers no capturan errores inesperados. Un worker caído y otro ok puede satisfacer asserts generales; deadlock puede colgar gate. | BLOQUE_tests.json |
| T05 | MEDIUM | E2E PG usa DATABASE_URL recibido sin aislamiento ni guardia de DB descartable. Hace setup inicial y escrituras; solo verifica prefijo postgresql. | BLOQUE_tests.json |
| T06 | LOW | Cierre, devolución y recepción frontend solo mockean éxito; falta rechazar promesas, mantener diálogo/datos, bloquear doble submit y evitar callback éxito/refresh falso ante error. | BLOQUE_tests.json |
| T07 | INFORMATIONAL | Fixtures por defecto suplantan auth como superusuario. Las suites de negocio prueban DB y rutas pero no autenticación JWT; api_usage Uvicorn también fakea auth. Negativos existentes en suites dedicadas sí son sustantivos y E2E SQLite autentica realmente. | BLOQUE_tests.json |
| UTIL-01 | HIGH | Arranque Windows resembra PostgreSQL y puede sobrescribir stock existente | BLOQUE_utilities.json |
| UTIL-02 | HIGH | cleanup_v2 elimina documentación canónica | BLOQUE_utilities.json |
| UTIL-03 | MEDIUM | Calendar pierde botones accesibles para navegar meses | BLOQUE_utilities.json |
| UTIL-04 | LOW | Progress omite valor semántico ARIA | BLOQUE_utilities.json |
| UTIL-05 | MEDIUM | test-system tolera tests frontend fallidos y concluye éxito | BLOQUE_utilities.json |
| UTIL-06 | MEDIUM | Quickstart canónico llama setup faltante | BLOQUE_utilities.json |
| UTIL-07 | MEDIUM | Simulaciones n8n no autentican discovery protegido y simulan éxito por prints | BLOQUE_utilities.json |
| UTIL-08 | MEDIUM | Configurador PostgreSQL rompe credenciales con caracteres normales e interpola SQL privilegiado | BLOQUE_utilities.json |
| UTIL-09 | LOW | Root check_*.py auditan SQLite legacy y ocultan fallos | BLOQUE_utilities.json |
| UTIL-10 | MEDIUM | reset_system anuncia reseteo aunque no aplica a PostgreSQL y mata uvicorn globalmente | BLOQUE_utilities.json |
| UTIL-11 | LOW | Dialog y AlertDialog fuerzan pantalla completa también desktop | BLOQUE_utilities.json |
| UTIL-12 | LOW | ChartTooltipContent oculta valores cero | BLOQUE_utilities.json |
| DOC-01 | MEDIUM | LIMITATIONS contradice conversión USD implementada | BLOQUE_utilities.json |
| DOC-02 | MEDIUM | Guías de producción vigentes aparentes omiten gates y dan falsa preparación | BLOQUE_utilities.json |
| DOC-03 | MEDIUM | Integración n8n tiene JSON corrupto y contratos obsoletos | BLOQUE_utilities.json |
| PROD-01 | HIGH | Producción no tiene provenance verificable y conserva cambios fuera de GitHub | VERIFICACIONES.md |
| PROD-02 | HIGH | Backup off-site obligatorio sin destino configurado | VERIFICACIONES.md |


## Ampliación y rectificación

Consultar CONTINUACION_02.md para nuevos hallazgos. FE-01: retirar afirmación de persistencia inconsistente; el guard ORM responde HTTP400 y rollback. HALLAZGOS.json contiene estado vigente.
