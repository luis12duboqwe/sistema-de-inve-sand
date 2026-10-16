#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cp "$ROOT/cleanup_v2.sh" "$TMP/cleanup_v2.sh"
printf 'Do not delete me\n' > "$TMP/COMIENZA_AQUI.md"
printf 'Original manual\n' > "$TMP/SECURITY.md"
(cd "$TMP" && bash ./cleanup_v2.sh --plan >/dev/null)
if (cd "$TMP" && bash ./cleanup_v2.sh >/dev/null 2>&1); then
  echo 'cleanup legacy should reject destructive action' >&2
  exit 1
fi
grep -Fxq 'Do not delete me' "$TMP/COMIENZA_AQUI.md"
grep -Fxq 'Original manual' "$TMP/SECURITY.md"
if grep -Eiq 'init_db\.py[[:space:]]+--with-data' <(grep -v '^REM' "$ROOT/start-backend.bat"); then
  echo 'Windows launcher must never seed sample data' >&2
  exit 1
fi
echo 'Legacy utilities safe guard tests OK'
