#!/usr/bin/env bash
# Retired legacy configurator. Unescaped privileged SQL and raw passwords are unsafe.
set -euo pipefail
if [[ "${1:-}" == "--plan" ]]; then
  cat <<'EOF'
setup-postgres.sh ha sido retirado por riesgos de inyección SQL y exposición
de contraseñas; NO crea roles, tablas, ni modifica archivos .env.

Configuración compatible:
  - Desarrollo: crear PostgreSQL descartable y backend/.env manualmente.
  - Producción: ejecutar deploy/prepare-prod-env.sh, configurar secretos externos,
    luego deploy/validate-prod.sh y el procedimiento en docs/PRODUCCION_FINAL.md.
  - Migraciones: usar las migraciones versionadas de la API y verificar el plan DR.
Nunca compartir ni imprimir contraseñas en consola.
EOF
  exit 0
fi
echo "Bloqueado: configuración PostgreSQL legacy insegura. Ejecutar --plan." >&2
exit 2
