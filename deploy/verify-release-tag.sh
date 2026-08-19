#!/usr/bin/env bash

set -euo pipefail

ref="${GITHUB_REF:-}"
sha="${GITHUB_SHA:-}"
repository="${GITHUB_REPOSITORY:-}"
release_issue="${RELEASE_PREREQUISITE_ISSUE:-38}"

case "$ref" in
  refs/tags/v*) ;;
  *)
    echo "No es un tag estable v*; guard de procedencia no aplica."
    exit 0
    ;;
esac

[ -n "$sha" ] || { echo "GITHUB_SHA es obligatorio para validar un tag estable" >&2; exit 1; }
[ -n "$repository" ] || { echo "GITHUB_REPOSITORY es obligatorio para validar un tag estable" >&2; exit 1; }
[ -n "${GH_TOKEN:-}" ] || { echo "GH_TOKEN es obligatorio para consultar el checklist de producción" >&2; exit 1; }
[[ "$release_issue" =~ ^[1-9][0-9]*$ ]] || { echo "RELEASE_PREREQUISITE_ISSUE debe ser un número positivo" >&2; exit 1; }

# El tag debe apuntar exactamente al HEAD actual de main. Esto evita publicar
# un tag estable desde una rama, un commit antiguo o un SHA que nunca pasó por
# el flujo protegido de main.
git fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main >/dev/null

tagged_commit="$(git rev-parse "${sha}^{commit}")"
main_commit="$(git rev-parse 'origin/main^{commit}')"

if [ "$tagged_commit" != "$main_commit" ]; then
  echo "Tag estable rechazado: apunta a $tagged_commit pero main está en $main_commit" >&2
  exit 1
fi

issue_state="$(gh api "repos/${repository}/issues/${release_issue}" --jq '.state')"
if [ "$issue_state" != "closed" ]; then
  echo "Tag estable rechazado: Issue #${release_issue} debe estar cerrado (estado actual: ${issue_state})" >&2
  exit 1
fi

echo "Procedencia del tag estable OK: commit=$tagged_commit, Issue #${release_issue}=closed"
