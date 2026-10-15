#!/usr/bin/env bash
# Desactivado: nunca borrar archivos SQLite ni terminar Uvicorn globalmente.
set -euo pipefail
if [[ "${1:-}" == "--plan" ]]; then
  cat <<'EOF'
El antiguo reset_system.sh ha sido retirado.
NO borra archivos, NO mata procesos y NO manipula PostgreSQL.
Para reiniciar la aplicación, utilice el mecanismo de despliegue autorizado.
Para ensayar un borrado/reset, cree una base de pruebas descartable y aislada.
EOF
  exit 0
fi
echo "Operación BLOQUEADA: reset_system.sh es destructivo e incompatible con PostgreSQL. Use --plan." >&2
exit 2
