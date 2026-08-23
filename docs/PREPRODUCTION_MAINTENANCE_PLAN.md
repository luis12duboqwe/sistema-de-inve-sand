# Pre-production maintainability pass

## Scope

This maintenance pass intentionally excludes all real production operations: no VPS changes, no real-data migration, no off-site credential setup, no staging/DR execution, no stable tags, and no release deployment.

The goal is to improve maintainability and test confidence while preserving the business behavior already hardened in PR #60.

## Priorities

1. Keep sale completion independent from daily-close validation in every frontend path, including bulk completion.
2. Reduce `src/App.tsx` by extracting pure permission, filtering, and dashboard/view-model logic into focused modules/hooks with regression tests.
3. Reduce `backend/app/routers/ai_intelligence.py` by moving pure helpers and cohesive non-routing logic into service/helper modules without changing endpoint contracts.
4. Consolidate or clearly isolate canonical-vs-legacy routing where this can be done without changing runtime behavior; do not perform a risky wholesale rewrite before production.
5. Add focused tests to weak but important areas, prioritizing auth/session boundaries, IMEI integrity, WebSocket auth/idle behavior, Super Admin protected operations, production guards, and report/transfer invariants.
6. Remove stale comments/documentation that contradict the canonical state machine or current production policy.
7. Keep the full CI/security gates unchanged.

## Guardrails

- Do not deploy or touch the VPS.
- Do not migrate or modify real business data.
- Do not create `v*` tags.
- Do not weaken test, audit, dependency, or Trivy gates.
- Do not change stock, refund, cancellation, transfer, daily-close, or IMEI semantics unless a concrete regression is found and covered by a focused test.
- Prefer small extraction refactors with preserved public behavior over large rewrites.

## Deliberately deferred debt

The repository still contains canonical/legacy shadow layers around some orders, reports, transfers, and Super Admin routes. They are not being removed wholesale in this pass. Consolidation should happen only after endpoint-contract equivalence and PostgreSQL concurrency behavior are demonstrated with focused tests; deleting these layers now would create more release risk than value.

## Acceptance

- Frontend lint/tests/build green.
- Backend PostgreSQL suite green.
- E2E runtime and PostgreSQL concurrency green.
- Dependency and container security scans green.
- Focused regression tests added for every behavior corrected or moved.
- No production/configuration prerequisites in Issue #38 are falsely marked complete.
