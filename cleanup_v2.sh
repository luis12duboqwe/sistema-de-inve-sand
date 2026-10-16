#!/usr/bin/env bash
# Script LEGACY retirado por riesgo de borrar documentación canónica.
# No mover, sobreescribir o borrar ningún archivo desde esta utilidad.
set -euo pipefail

case "${1:-}" in
  --plan)
    cat <<'EOF'
cleanup_v2.sh está retirado. Este comando es solo informativo.
La documentación canónica y AGENTS deben mantenerse versionados en Git.
Para reorganizar documentación, preparar un PR con cambios explícitos,
comparar destinos y revisar el diff antes de aplicarlos.
EOF
    ;;
  *)
    echo "Operación bloqueada: cleanup_v2.sh era destructivo. Use --plan." >&2
    exit 2
    ;;
esac
