# AGENTS.md — sistema-de-inve-sand

These repository instructions extend the user's global Codex instructions. Follow the stricter rule when they differ.

## Mission and source of truth
This is a multi-location inventory and sales system intended for real business use. Preserve correctness, traceability, and recoverability over speed or cosmetic improvements.

Before changing code, read the relevant canonical documentation:
- `README.md`
- `COMIENZA_AQUI.md`
- `docs/PRODUCCION_FINAL.md` for production/deployment work
- `CHECKLIST_PRODUCCION.md` and `DEPLOY_CHECKLIST.md` for release work
- `docs/ARQUITECTURA.md` for architecture-sensitive changes

Historical audit documents are reference material only. When they conflict with current canonical docs or current code, verify the current implementation and follow the canonical current state.

## Current architecture
- Frontend: React 19 + TypeScript + Vite.
- Backend: FastAPI + SQLAlchemy.
- Production database: PostgreSQL 16.
- Deployment: Docker Compose.
- Production frontend is API-only. Never add a production fallback that writes business data to browser/local storage when the backend is unavailable.
- Security includes JWT, RBAC, location permissions, rate limiting, production guards, and audit behavior.
- Production operations include versioned migrations, structured logging/monitoring options, verified backups, off-site replication, and DR procedures.

Do not replace these architectural choices as incidental cleanup. Architecture changes require explicit design approval.

## Business invariants
Treat these as non-negotiable unless an approved design explicitly changes the business rule:
- IMEI/serial values that are required to be unique must not silently duplicate.
- A normal business transaction must never create negative stock.
- Sales, purchases, returns, transfers, financing, and multi-payment operations must be atomic/consistent from the business perspective.
- A failed transaction must not leave partial stock, payment, or ledger effects.
- Transfers must follow explicit lifecycle transitions and must neither duplicate nor lose stock between locations.
- Location-scoped users must not read or mutate unauthorized location data.
- Authorization is enforced server-side; UI visibility is never the security boundary.
- Audited/sensitive operations must retain their audit trail.
- Financial totals must reconcile to underlying transactions; do not validate accounting behavior only from rendered UI totals.
- Migration failure must fail safely; the application must not knowingly accept traffic with a partially migrated critical schema.

For concurrency-sensitive inventory changes, reason about simultaneous requests and database transaction boundaries, not only single-request happy paths.

## Change workflow
1. Inspect the relevant implementation, tests, migrations, API contracts, and recent related changes before editing.
2. Reproduce bugs before fixing them.
3. For behavior changes, add or update a failing regression/feature test first unless the user explicitly approves a TDD exception.
4. Make the smallest coherent change that fixes the root cause.
5. Do not mix unrelated refactors, dependency upgrades, formatting sweeps, or speculative features into the same change.
6. If implementation reveals an architectural change, stop and obtain design approval before continuing.
7. Review the final diff for accidental behavior/configuration changes.

Use isolated branches/worktrees/agents for independent tasks. Do not let parallel agents modify the same files or shared migration state without explicit coordination.

## Database and migrations
- PostgreSQL is the production truth. Do not validate production-critical database behavior solely against SQLite or mocks.
- Preserve migration ordering/version tracking and startup schema validation.
- Schema/data migrations must be safe for existing production-like data.
- For destructive or large transformations, define recovery/rollback and verify it.
- Never silently reset, recreate, truncate, or reseed production data as a migration shortcut.
- Changes involving stock, payments, transfers, IMEI uniqueness, financing, or permissions require database-backed tests where practical.

## API, auth, and frontend
- Preserve the production API-only policy.
- Do not introduce a client-side bypass for backend validation, RBAC, location permissions, stock checks, or financial rules.
- Treat API schema/status-code changes as contracts: update callers and tests together.
- Authentication/authorization changes require negative tests, not only successful-access tests.
- User-visible critical flows should be exercised through E2E/browser verification when tooling permits.

## Verification matrix
Run the strongest checks relevant to the changed surface. Do not claim a check passed unless it was run fresh and its output/exit status was inspected.

Frontend baseline:
```bash
npm run lint
npm run test:coverage
npm run build
```

Backend baseline:
```bash
cd backend
pytest --cov=app --cov-report=term-missing -ra
```

Primary E2E:
```bash
pytest -q tests/test_health_endpoints.py
pytest -q tests/e2e/test_runtime_e2e.py tests/e2e/test_business_flows_e2e.py
pytest -q tests/e2e/test_postgres_runtime_e2e.py
```

For a narrow change, targeted tests may be run during iteration, but before declaring the work complete run the applicable broader gates. If an expected gate cannot run because infrastructure/secrets are unavailable, state that explicitly and downgrade the completion status.

## Production/release gate
The repository being code-complete or locally green is not equivalent to being production-verified.

Never call a release production-ready until the applicable real operational gates are evidenced, including:
- final CI required checks green;
- `./deploy/validate-prod.sh` succeeds with real production domain/secrets;
- off-host backup destination is configured;
- backup integrity is verified;
- a restore/DR drill has succeeded in the intended staging/production procedure;
- required branch protection/checks are configured;
- deployment health and rollback path have been verified.

Use the repository's canonical production/release scripts and docs rather than inventing alternate deployment procedures without approval.

## Secrets and safety
- Never commit `.env` production secrets, tokens, credentials, private keys, database dumps containing real customer/business data, or rclone credentials.
- Do not weaken security gates merely to make CI pass.
- Do not disable tests, RBAC, rate limits, migration guards, backup verification, or production validation to bypass a failure.
- Investigate root cause instead.

## Completion language
Report status precisely:
- IMPLEMENTED: code/config exists.
- TESTED: applicable automated checks passed.
- INTEGRATED: change is merged/integrated and integration checks passed.
- DEPLOYED: change is running in the target environment.
- VERIFIED IN PRODUCTION: real production behavior/operational gates were verified.

Do not use "100% complete", "production-ready", "fixed", or equivalent as shorthand for a weaker state.

When blocked, report the exact blocker, the evidence already obtained, and the next executable action.


## SoftMobile audit execution and continuity protocol (2026-10-14)

These rules supplement all existing security, release, and business-invariant requirements above.

### Authority of environments
- Treat GitHub `main`, the current PRs, CI runs, and tracked documentation as the authoritative code history. Verify the precise branch and commit before making claims.
- Use an isolated branch and PR for proposed changes. Do not edit production or a dirty VPS worktree as the default development workflow.
- Use the VPS for read-only deployment verification, service health, logs, configuration comparison, and authorized staging checks; never infer production readiness solely from repository state.
- Compare deployed revisions and runtime settings with GitHub before declaring a deployment verified.

### Complete audit blocks, not micro-reviews
- Plan a substantial, bounded audit block that covers implementation, dependencies, relevant tests, and observed behavior; carry it through as far as the available tools permit.
- Do not stop after listing files, counting tests, or running syntax checks and describe that as a completed audit.
- Audit critical business flows end-to-end: authentication and location-scoped RBAC; products, stock and IMEI; purchases, sales and multi-payment; financing, transfers, returns and warranty; analytics; AI conversations and messaging channels; migrations, backup, restore and deployment.
- Examine critical functions and transaction boundaries individually where needed. A static inventory is not evidence of correctness.
- Distinguish confirmed defects from hypotheses, and attach a reproduction or precise code evidence.

### Evidence and testing
- For each block, record exact GitHub commit/branch, scope, findings, severity, file/line references, executed commands, results and unresolved limitations.
- Classify status as NOT REVIEWED, IMPLEMENTED, TESTED, STAGING VERIFIED, PRODUCTION VERIFIED or BLOCKED. Do not count skipped tests as passing.
- Run applicable backend PostgreSQL-backed tests, frontend tests/build/lint, CI checks and business-flow/browser tests. Never point destructive tests at production data.
- Investigate blocked or skipped suites rather than treating a zero exit code as a successful test run.
- Do not claim 100% completion, readiness or a passing gate without reproducible evidence.

### Durable project ledger
- Maintain a versioned audit ledger in `docs/auditoria-continua/` (or another explicitly designated tracked location) through a PR. Keep an index of audited modules, pending modules, confirmed findings, tests and next executable steps.
- At the beginning of each new session, read the current ledger, GitHub branch/PR state and recent commits before starting new work.
- Preserve useful findings from prior work, but independently verify them against the current revision; avoid repeating already verified work without a change or a reason.
- Never commit secrets, customer records, raw environment values, production database extracts or sensitive logs to the ledger.

### Reporting and autonomy
- Prefer a consolidated report after a meaningful block, rather than narrating each command or sending repeated small progress messages.
- Continue independently through safe, non-destructive investigation. If one tool is blocked, move to another legitimate task or authorized tool without bypassing safety restrictions.
- Ask for approval for risky, costly, destructive, irreversible or production-changing actions and architectural decisions; never treat this protocol as blanket authorization.
- Clearly state when a tool is blocked or a task cannot be completed. Do not imply background execution after a response unless a scheduled task or active process genuinely exists.
- Finish the full audit with one prioritized, evidence-based action plan: critical blockers first, dependencies, tests, PR sequencing, staging validation, production release gates and rollback.

### Working standard
Optimize for demonstrable progress, continuity, data safety and a verifiable outcome—not the number of tool calls, plugins installed, or interim updates.
