# Continuación 02 — auditoría, sin correcciones

Lecturas completas nuevas: 81. Cobertura: 552/653 (84.53%).

## OBS-01 — Etiquetas métricas ilimitadas para rutas arbitrarias

REPRODUCED_ISOLATED; HIGH

Veinte rutas /uploads diferentes que devuelven 404 crean veinte series de contador y veinte de histograma. La normalización mantiene segmentos arbitrarios y /uploads está exento del limitador general.

Impacto: Memoria y cardinalidad de métricas pueden crecer con peticiones externas.

Reproducción: Ejecutar TestClient con veinte URL únicas inexistentes bajo /uploads y contar etiquetas antes/después. No se envió carga a producción.

Recomendación: Etiquetar por plantilla de ruta y limitar rutas desconocidas.

Pruebas necesarias: Comprobar cardinalidad constante con rutas desconocidas y límites de uploads.

## OBS-02 — Contexto de logs global se mezcla entre peticiones async

REPRODUCED_ISOLATED; MEDIUM

LogContext sustituye LogRecordFactory global. Contextos A/B solapados atribuyen el log de A a B y dejan una factoría anterior tras salir.

Impacto: Correlación y auditoría de incidentes pueden atribuir peticiones al identificador equivocado.

Reproducción: Intercalar enter A, enter B, log A, exit A, exit B.

Recomendación: Usar contexto por tarea y factoría estable.

Pruebas necesarias: Prueba async de dos solicitudes con correlación independiente y restauración.

## OBS-03 — Inicialización duplicada de Sentry sobrescribe configuración

REPRODUCED_ISOLATED; MEDIUM

Dos inicializadores llaman init del SDK; el segundo omite opciones de profiling/PII presentes en el primero. Verificado con SDK simulado, sin conexión a Sentry.

Impacto: Telemetría configurada puede diferir de lo esperado.

Reproducción: Configurar DSN ficticio y registrar las dos llamadas con DummySDK.

Recomendación: Unificar inicialización y política de opciones.

Pruebas necesarias: Una inicialización con opciones finales explícitas.

## MODEL-01 — Modelo analytics no puede importarse

REPRODUCED_ISOLATED_LATENT; LOW

SQLAlchemy rechaza el atributo declarativo reservado metadata con InvalidRequestError. El módulo no está importado por el modelo canónico; no afecta el arranque observado.

Impacto: Integrar posteriormente ese módulo rompería la importación.

Reproducción: Importar app.models.analytics en subproceso aislado.

Recomendación: Renombrar atributo Python manteniendo nombre de columna si procede.

Pruebas necesarias: Importación de todos los módulos de modelos.

## FE-12 — Exportación CSV corrompe comillas y conserva fórmulas

REPRODUCED_ISOLATED; MEDIUM

El campo a"b se serializa con barra invertida, no doble comilla CSV; csv.reader no recupera el valor original. =1+1 queda sin neutralizar. No se ejecutó una fórmula en una hoja real.

Impacto: Datos exportados pueden alterarse; riesgo de fórmulas al abrir hojas.

Reproducción: Exportar a"b y =1+1 con el helper real y leer con csv.reader.

Recomendación: Escapado CSV estándar y política de celdas formula.

Pruebas necesarias: Roundtrip de comillas, saltos, separadores y prefijos de fórmula.

## FE-13 — Reporte excluye costo de regalías y usa fecha de creación

REPRODUCED_ISOLATED; MEDIUM

Venta total 1000, costo pagado 600 y regalo costo 100 produce margen 40%, aunque corresponde 30%. Venta creada en septiembre y completada en octubre se asigna a septiembre.

Impacto: Rentabilidad y cierres mensuales pueden informar valores incorrectos.

Reproducción: Ejecutar generateReportData con ambos fixtures del JSON de reproducción.

Recomendación: Incluir todo costo entregado y definir fecha contable coherente.

Pruebas necesarias: Regalías y órdenes que cruzan meses.

## FE-14 — Catálogo público nuevo usa API localhost por defecto

CONFIRMED_STATIC_PENDING_BROWSER; HIGH

PublicCatalog lee settings_api_url con localhost:8000/api por defecto. La ruta pública se muestra antes de BackendConnectionCheck; un visitante sin KV no normaliza la API al origen. Incluye destino WhatsApp de ejemplo.

Impacto: Visitantes nuevos pueden no ver catálogo ni contactar al negocio correcto.

Reproducción: Abrir /catalog en navegador limpio desplegado; prueba browser todavía pendiente.

Recomendación: Resolver API pública por origen y configurar contacto real.

Pruebas necesarias: Visita limpia de producción sin almacenamiento previo.

## FE-15 — Errores de API se presentan como historiales vacíos

CONFIRMED_STATIC; MEDIUM

Capturas de errores retornan [] o null en varios lectores; componentes muestran ausencia de datos o todo al día.

Impacto: Interrupciones pueden ocultar historial y tareas pendientes.

Reproducción: Simular error de API en lectores de historial/training queue y observar resultado vacío. Runtime UI pendiente.

Recomendación: Propagar estado de error distinguible del resultado vacío.

Pruebas necesarias: Error HTTP/red y resultados realmente vacíos.

## SYNC-01 — Sincronización usa IDs locales y continúa tras dependencias fallidas

REPRODUCED_MOCK_API; HIGH

Ubicación local 1 creada como remota 100; creación producto envía location_id=1. Si creación producto 7 falla, update siguiente usa ID7 y se marca sincronizado.

Impacto: Puede escribir entidad remota equivocada o asociar inventario a otra sucursal si coinciden IDs.

Reproducción: API mock del servicio real con remapeo 1→100 y creación fallida 7.

Recomendación: Remapear todas las claves y bloquear dependencias sin ID remoto.

Pruebas necesarias: IDs divergentes, colisiones y fallos de creación antes de update.

## SYNC-02 — Diario pierde eventos concurrentes y pendientes al truncar

REPRODUCED_MEMORY_KV; MEDIUM

Dos recordEvent simultáneos persisten uno. Al añadir sobre 5000 eventos pendientes se elimina el pendiente más antiguo.

Impacto: Cambios locales pueden perderse sin sincronizar.

Reproducción: Promise.all con dos eventos; después agregar uno a 5000 pendientes usando KV en memoria.

Recomendación: Persistencia serializada y retención que preserve pendientes.

Pruebas necesarias: Concurrencia y límite con todos los eventos pendientes.

## SA-01 — Cancelación administrativa no bloquea estado del traslado

GROUNDED_RISK_PENDING_POSTGRES; HIGH

Lee traslado pendiente sin FOR UPDATE y luego bloquea stock sin refrescar estado. Puede competir con confirmación canónica; requiere comprobar intercalación PostgreSQL.

Impacto: Riesgo de cancelar traslado confirmado o liberar reservas agregadas ajenas.

Reproducción: Coordinar confirmación y cancelación en PostgreSQL descartable; no ejecutado.

Recomendación: Bloquear traslado y revalidar estado dentro de transacción coherente.

Pruebas necesarias: Carrera confirm/cancel con otra reserva del mismo producto.

## SA-02 — Purga parcial puede dejar totales y devoluciones incoherentes

GROUNDED_STATIC_CONDITIONAL; HIGH

Purga elimina ítems del producto de órdenes mixtas sin reconciliar totales/pagos; devuelve eliminación de todas las devoluciones de órdenes que contienen el producto. Producción tiene purga desactivada según comprobación anterior.

Impacto: Si se habilita, pérdida de trazabilidad de otros productos y cifras históricas inconsistentes.

Reproducción: Fixture mixto en DB descartable; no se ejecutó ninguna purga.

Recomendación: Definir política de retención y consistencia antes de habilitar.

Pruebas necesarias: Órdenes/devoluciones mixtas y validación de totales.

## TEST-08 — Pruebas de invariantes aceptan pérdida de actualizaciones

CONFIRMED_STATIC_TEST_ORACLE; MEDIUM

Threads parten de stock5 y pueden escribir1; el test sólo exige no negativo. Reservas simultáneas y errores recolectados no tienen oráculo estricto de conservación.

Impacto: Tests verdes no demuestran integridad concurrente de stock.

Reproducción: Revisar asserts y errores recolectados; ejecución PostgreSQL pendiente.

Recomendación: Afirmar stock exacto, reservas, resultados y ausencia de errores no previstos.

Pruebas necesarias: Transacciones concurrentes reales con conservación de cantidades.

FE-01 rectificado: guard before_flush rechaza desglose incorrecto; no persistencia inconsistente confirmada.
