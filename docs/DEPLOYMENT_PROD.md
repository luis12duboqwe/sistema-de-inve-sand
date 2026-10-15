# Despliegue productivo — referencia
La guía histórica de despliegue manual fue sustituida por el documento canónico:

**[PRODUCCION_FINAL.md](PRODUCCION_FINAL.md)**

Para considerar un release apto deben coincidir el commit SHA de GitHub, la imagen construida, la configuración efectiva del VPS y el estado de la base de datos. La evidencia pendiente de **provenance del VPS** y **backup off-site realmente probado** impide afirmar que el entorno esté listo.

Nunca iniciar el backend productivo con `uvicorn --reload`, SQLite, modo KV del navegador o datos de muestra. No ejecutar migraciones, restauraciones ni scripts destructivos en producción como respuesta a un fallo de CI. Para restaurar, validar checksum y usar primero una base **nueva y aislada**, sin modificar la que sirve clientes.

Comandos de configuración, CI, Docker Compose, health, DR y rollback: consultar exclusivamente el runbook canónico.
