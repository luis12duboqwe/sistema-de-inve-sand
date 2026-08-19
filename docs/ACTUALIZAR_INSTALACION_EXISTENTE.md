# Actualizar una instalación existente sin perder datos

Este documento aplica a instalaciones de Softmobile/Sistema de Inventario que **ya están en uso**. La actualización no debe tratarse como una instalación nueva.

## Regla principal

**No borrar ni reemplazar los datos actuales para actualizar el código.**

El proyecto reconoce dos fuentes históricas de datos:

1. `backend/inventory.db` — base SQLite usada por el backend local de Windows.
2. Datos del navegador — claves `spark-kv-*` usadas por el modo local del frontend.

Ambas deben preservarse antes de un cambio de versión o de mover el sistema a PostgreSQL.

## 1. Si usas el backend local de Windows (`inventory.db`)

El script histórico `start-backend.bat` reutiliza `backend/inventory.db` cuando ya existe. La versión actual mantiene esa compatibilidad en modo local/desarrollo.

Al arrancar el backend actualizado:

1. SQLAlchemy crea únicamente tablas que todavía no existan.
2. Las migraciones versionadas detectan columnas pendientes.
3. Si la base es SQLite y hay migraciones pendientes, se crea primero una copia consistente en:

   `backend/backups/inventory.pre-migration-<fecha>.db`

4. La base original se actualiza **en el mismo archivo**; no se recrea ni se vacía.
5. Las migraciones se registran en `schema_migrations` y son idempotentes.
6. Si el esquema no puede actualizarse de forma segura, el backend debe fallar al arrancar en lugar de operar con una base parcialmente migrada.

### Qué no hacer

- No borrar `backend/inventory.db`.
- No ejecutar `init_db.py --with-data` sobre una instalación usada para intentar "actualizarla".
- No copiar una base de ejemplo encima de la base real.
- No eliminar `backend/backups` hasta haber comprobado que la versión nueva funciona.

## 2. Si usaste el modo local del navegador

Los datos locales continúan usando las mismas claves `spark-kv-*`; actualizar el código no las borra.

Antes de cualquier cambio importante:

1. Abre el sistema desde el mismo navegador/perfil donde lo utilizas normalmente.
2. Ve a **Diagnóstico de Almacenamiento**.
3. Pulsa **Exportar**.
4. Guarda el archivo JSON fuera de la carpeta del proyecto.

El formato de backup actual (`softmobile-browser-backup`, versión 3) incluye **todas las claves KV existentes**, no sólo productos/stock/órdenes. Esto protege, entre otros, IMEIs, transferencias, devoluciones, historial, clientes, usuarios/roles, bancos, financiación, FAQs, configuración y futuras claves que se agreguen después.

La importación sigue aceptando también los backups antiguos que sólo contenían:

- perfiles;
- productos;
- stock;
- órdenes;
- items de orden.

> Importante: un backup del navegador preserva los datos locales, pero no significa que ya estén cargados en PostgreSQL. La migración/cutover a producción debe verificarse antes de retirar la instalación local.

## 3. Crear una huella privada de datos antes y después

`backend/upgrade_audit.py` es una herramienta **de solo lectura respecto a la base de datos**. No modifica filas ni ejecuta migraciones. Para detectar corrupción que conserve los mismos conteos, calcula fingerprints HMAC-SHA256 por columna y por fila, ligados a la clave primaria. El JSON no contiene nombres de clientes, teléfonos, IMEIs, usernames, correos, hashes de contraseña ni otros valores originales.

La primera vez crea una clave privada local `.upgrade-audit.key`. Esa clave **no se incluye en el snapshot, no se debe subir a Git y debe conservarse para generar todos los snapshots del mismo corte**. `.gitignore` excluye tanto la clave como `upgrade-*.json`.

Antes de actualizar la instalación SQLite:

```bash
cd backend
python upgrade_audit.py snapshot --sqlite inventory.db --output upgrade-before.json
```

Después de actualizar el SQLite existente, reutilizando la misma `.upgrade-audit.key`:

```bash
python upgrade_audit.py snapshot --sqlite inventory.db --output upgrade-after-sqlite.json
python upgrade_audit.py compare upgrade-before.json upgrade-after-sqlite.json --output upgrade-compare-sqlite.json
```

El comando `compare` termina con código `0` únicamente cuando los datos históricos siguen representados sin diferencias. Las tablas y columnas **nuevas** del software actualizado están permitidas. En cambio, si una columna que existía en el origen desaparece del destino, la comparación falla para impedir que un campo histórico se descarte silenciosamente.

Además del contenido de cada columna, la comparación revisa:

- conteo de filas de todas las tablas del origen;
- productos activos;
- stock disponible, reservado y defectuoso;
- importe total de órdenes;
- cantidad total de items vendidos;
- IMEIs vendidos/no vendidos;
- usuarios activos y superusuarios;
- cantidades enviadas, recibidas y faltantes en transferencias.

Los snapshots sólo son comparables si se generaron con la misma clave privada. Si la clave cambia o se pierde, la herramienta rechaza la comparación en lugar de asumir compatibilidad.

## 4. Migrar `inventory.db` a PostgreSQL

Cuando se prepare el servidor definitivo, usar:

```bash
cd backend
python migrate_sqlite_to_postgres.py --sqlite inventory.db
```

El migrador actual:

- no modifica el SQLite fuente;
- crea además `backups/inventory.pre-postgres-migration-<fecha>.db`;
- refleja el esquema real de cada tabla SQLite antigua;
- copia sólo las columnas que existen tanto en el origen como en el modelo actual;
- rechaza esquemas demasiado antiguos si falta un campo obligatorio que no puede reconstruirse de forma segura;
- se niega a mezclar automáticamente los datos con un PostgreSQL que ya tenga filas;
- permite `--truncate` sólo como acción explícita cuando el operador confirmó que el destino puede reemplazarse;
- repara las secuencias PostgreSQL después de copiar IDs históricos.

Después de migrar, crear la huella PostgreSQL con **la misma `.upgrade-audit.key`** y compararla con la huella original:

```bash
python upgrade_audit.py snapshot --database-url "$DATABASE_URL" --output upgrade-after-postgres.json
python upgrade_audit.py compare upgrade-before.json upgrade-after-postgres.json --output upgrade-compare-postgres.json
```

Si el SQLite antiguo contiene una columna histórica que el modelo PostgreSQL actual no conserva, `upgrade_audit.py compare` devuelve incompatibilidad. Ese caso debe resolverse explícitamente antes del corte; no se considera aceptable perder la columna sólo porque el resto de filas se copiaron.

**No cambiar la operación diaria a PostgreSQL si el reporte devuelve `compatible: false`.** El SQLite original sigue siendo la fuente de rollback hasta resolver cualquier diferencia.

## 5. Orden recomendado para una actualización real

1. Detener temporalmente el uso del sistema para evitar datos nuevos durante el corte.
2. Conservar la instalación actual intacta.
3. Exportar el backup completo del navegador si alguna vez se utilizó modo local.
4. Crear y custodiar `.upgrade-audit.key`; crear `upgrade-before.json` desde `inventory.db`.
5. Verificar/custodiar `backend/inventory.db` y sus backups.
6. Actualizar el código.
7. Arrancar primero contra la instalación local existente y comprobar que las migraciones terminan correctamente.
8. Crear `upgrade-after-sqlite.json` con la misma clave y exigir comparación compatible con `upgrade-before.json`.
9. Preparar PostgreSQL del servidor.
10. Migrar SQLite→PostgreSQL si SQLite contiene los datos operativos.
11. Crear `upgrade-after-postgres.json` con la misma clave y exigir comparación compatible con `upgrade-before.json`.
12. Ejecutar las operaciones críticas: login, permisos, inventario, venta/IMEI, transferencia y cierre diario.
13. Sólo entonces cambiar la operación diaria al servidor nuevo.
14. Mantener el backup SQLite, `.upgrade-audit.key`, los reportes de auditoría y el JSON del navegador durante el período de verificación/rollback.

## 6. Criterio de compatibilidad

Una versión nueva no se considera apta para esta instalación si requiere borrar la base, reiniciar inventario o descartar información histórica.

Antes del release estable deben pasar, como mínimo:

- prueba de migración PostgreSQL idempotente;
- prueba de actualización de un SQLite legado conservando filas existentes;
- prueba de creación de backup SQLite antes de migrar;
- prueba de exportación/restauración completa de KV del navegador;
- prueba de fingerprints privados que detecten corrupción de contenido aunque los conteos coincidan;
- prueba que rechace la pérdida de columnas históricas del origen;
- prueba real de snapshot contra PostgreSQL;
- CI, E2E y escaneos de seguridad existentes.

## 7. Rollback

Si una actualización local falla:

1. detener el backend nuevo;
2. conservar el archivo fallido, `.upgrade-audit.key` y los reportes `upgrade-*.json` para diagnóstico;
3. restaurar la copia `inventory.pre-migration-*.db` como `inventory.db`;
4. volver al código anterior;
5. no continuar la migración a producción hasta identificar la causa.

En una migración a PostgreSQL, **no se elimina el SQLite fuente**. Esto permite comparar o volver temporalmente a la instalación anterior durante la validación.
