#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
mkdir -p "$TMP_DIR/bin"

cat > "$TMP_DIR/bin/git" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "git $*" >> "${FAKE_CALLS_FILE:?}"
case "${1:-}" in
  fetch)
    exit "${FAKE_GIT_FETCH_EXIT:-0}"
    ;;
  rev-parse)
    case "${2:-}" in
      origin/main\^\{commit\}) printf '%s\n' "${FAKE_MAIN_COMMIT:-mainsha}" ;;
      *) printf '%s\n' "${FAKE_TAG_COMMIT:-tagsha}" ;;
    esac
    ;;
  *)
    echo "git falso recibió comando inesperado: $*" >&2
    exit 90
    ;;
esac
EOF
chmod +x "$TMP_DIR/bin/git"

cat > "$TMP_DIR/bin/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "gh $*" >> "${FAKE_CALLS_FILE:?}"
[ "${1:-}" = "api" ] || exit 91
printf '%s\n' "${FAKE_ISSUE_STATE:-closed}"
EOF
chmod +x "$TMP_DIR/bin/gh"

run_guard() {
  : > "$TMP_DIR/calls"
  env \
    PATH="$TMP_DIR/bin:$PATH" \
    FAKE_CALLS_FILE="$TMP_DIR/calls" \
    GH_TOKEN=fake-token \
    GITHUB_REPOSITORY=luis12duboqwe/sistema-de-inve-sand \
    RELEASE_PREREQUISITE_ISSUE=38 \
    "$@" \
    bash "$DEPLOY_DIR/verify-release-tag.sh"
}

# 1. Push normal a main/workflow manual: el guard no debe tocar GitHub ni Git.
main_output="$(run_guard GITHUB_REF=refs/heads/main GITHUB_SHA=mainsha)"
grep -Fq 'guard de procedencia no aplica' <<<"$main_output"
[ ! -s "$TMP_DIR/calls" ] || { echo "El guard consultó dependencias en un evento no-tag" >&2; exit 1; }

# 2. Tag v* sobre HEAD actual y checklist cerrado: éxito.
success_output="$(run_guard \
  GITHUB_REF=refs/tags/v3.0.0 \
  GITHUB_SHA=tag-event-sha \
  FAKE_TAG_COMMIT=samesha \
  FAKE_MAIN_COMMIT=samesha \
  FAKE_ISSUE_STATE=closed)"
grep -Fq 'Procedencia del tag estable OK' <<<"$success_output"
grep -Fq 'repos/luis12duboqwe/sistema-de-inve-sand/issues/38' "$TMP_DIR/calls"

# 3. Tag que no apunta al HEAD actual de main: rechazo antes de consultar el issue.
set +e
mismatch_output="$(run_guard \
  GITHUB_REF=refs/tags/v3.0.1 \
  GITHUB_SHA=tag-event-sha \
  FAKE_TAG_COMMIT=oldsha \
  FAKE_MAIN_COMMIT=newsha \
  FAKE_ISSUE_STATE=closed 2>&1)"
mismatch_status=$?
set -e
[ "$mismatch_status" -ne 0 ] || { echo "El guard aceptó un tag fuera del HEAD de main" >&2; exit 1; }
grep -Fq 'Tag estable rechazado: apunta a oldsha pero main está en newsha' <<<"$mismatch_output"
if grep -Fq 'gh api' "$TMP_DIR/calls"; then
  echo "El guard consultó el issue aunque la procedencia ya era inválida" >&2
  exit 1
fi

# 4. Tag correcto pero checklist #38 aún abierto: rechazo.
set +e
open_issue_output="$(run_guard \
  GITHUB_REF=refs/tags/v3.0.2 \
  GITHUB_SHA=tag-event-sha \
  FAKE_TAG_COMMIT=samesha \
  FAKE_MAIN_COMMIT=samesha \
  FAKE_ISSUE_STATE=open 2>&1)"
open_issue_status=$?
set -e
[ "$open_issue_status" -ne 0 ] || { echo "El guard aceptó un release con Issue #38 abierto" >&2; exit 1; }
grep -Fq 'Issue #38 debe estar cerrado' <<<"$open_issue_output"

# 5. Un tag no puede saltarse el chequeo si falta token.
set +e
missing_token_output="$(
  PATH="$TMP_DIR/bin:$PATH" \
  FAKE_CALLS_FILE="$TMP_DIR/calls" \
  GITHUB_REPOSITORY=luis12duboqwe/sistema-de-inve-sand \
  GITHUB_REF=refs/tags/v3.0.3 \
  GITHUB_SHA=samesha \
  GH_TOKEN='' \
  bash "$DEPLOY_DIR/verify-release-tag.sh" 2>&1
)"
missing_token_status=$?
set -e
[ "$missing_token_status" -ne 0 ] || { echo "El guard aceptó tag sin GH_TOKEN" >&2; exit 1; }
grep -Fq 'GH_TOKEN es obligatorio' <<<"$missing_token_output"

echo "Release tag guard tests OK"
