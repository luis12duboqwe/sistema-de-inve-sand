#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
npm run lint
npm run test:coverage
cd backend
if [ -f venv/bin/activate ]; then
  source venv/bin/activate
elif [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
else
  echo "No backend virtualenv: no tests run." >&2
  exit 1
fi
pytest --cov=app
echo "All checks passed."
