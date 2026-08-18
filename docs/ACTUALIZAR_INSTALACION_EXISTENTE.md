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

## 3. Migrar `inventory.db` a PostgreSQL

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

## 4. Orden recomendado para una actualización real

1. Detener temporalmente el uso del sistema para evitar datos nuevos durante el corte.
2. Conservar la instalación actual intacta.
3. Exportar el backup completo del navegador si alguna vez se utilizó modo local.
4. Verificar/custodiar `backend/inventory.db` y sus backups.
5. Actualizar el código.
6. Arrancar primero contra la instalación local existente y comprobar que las migraciones terminan correctamente.
7. Verificar conteos básicos antes/después: productos, stock, órdenes, IMEIs y usuarios.
8. Preparar PostgreSQL del servidor.
9. Migrar SQLite→PostgreSQL si SQLite contiene los datos operativos.
10. Verificar los mismos conteos y operaciones críticas en PostgreSQL.
11. Sólo entonces cambiar la operación diaria al servidor nuevo.
12. Mantener el backup SQLite y el JSON del navegador durante el período de verificación/rollback.

## 5. Criterio de compatibilidad

Una versión nueva no se considera apta para esta instalación si requiere borrar la base, reiniciar inventario o descartar información histórica.

Antes del release estable deben pasar, como mínimo:

- prueba de migración PostgreSQL idempotente;
- prueba de actualización de un SQLite legado conservando filas existentes;
- prueba de creación de backup SQLite antes de migrar;
- prueba de exportación/restauración completa de KV del navegador;
- CI, E2E y escaneos de seguridad existentes.

## 6. Rollback

Si una actualización local falla:

1. detener el backend nuevo;
2. conservar el archivo fallido para diagnóstico;
3. restaurar la copia `inventory.pre-migration-*.db` como `inventory.db`;
4. volver al código anterior;
5. no continuar la migración a producción hasta identificar la causa.

En una migración a PostgreSQL, **no se elimina el SQLite fuente**. Esto permite comparar o volver temporalmente a la instalación anterior durante la validación.
