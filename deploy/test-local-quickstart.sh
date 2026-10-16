#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP="$(mktemp -d)"
trap 'rm -rf "$TEMP"' EXIT
printf '%s\n' "important production data" > "$TEMP/inventory.db"
mkdir -p "$TEMP/bin"
cat > "$TEMP/bin/pkill" <<'EOF'
#!/usr/bin/env bash
echo "Forbidden process-wide kill" >&2
exit 77
EOF
chmod +x "$TEMP/bin/pkill"
(
 cd "$TEMP"
 PATH="$TEMP/bin:$PATH" bash "$ROOT/reset_system.sh" --plan >/dev/null
 if PATH="$TEMP/bin:$PATH" bash "$ROOT/reset_system.sh" >/dev/null 2>&1; then
   echo "Legacy reset must fail closed" >&2; exit 1
 fi
)
grep -Fxq "important production data" "$TEMP/inventory.db"
# Deprecated SQL configurator is read-only and must never invoke psql/sudo/sed.
cat > "$TEMP/bin/psql" <<'EOF'
#!/usr/bin/env bash
echo 'Unexpected SQL operation from retired setup' >&2
exit 97
EOF
chmod +x "$TEMP/bin/psql"
(
 cd "$TEMP"
 PATH="$TEMP/bin:$PATH" bash "$ROOT/setup-postgres.sh" --plan >/dev/null
 if PATH="$TEMP/bin:$PATH" bash "$ROOT/setup-postgres.sh" >/dev/null 2>&1; then
   echo 'Legacy SQL configurator must fail closed' >&2; exit 1
 fi
)
bash -n "$ROOT/setup-postgres.sh"

# Local launcher refuses production and missing prerequisites without sudo/pkill.
if ENVIRONMENT=production bash "$ROOT/start-all.sh" >/dev/null 2>&1; then
  echo "Local launcher accepted production" >&2; exit 1
fi
bash -n "$ROOT/start-all.sh"
bash -n "$ROOT/reset_system.sh"
echo "Legacy reset and local quickstart safeguards OK"
