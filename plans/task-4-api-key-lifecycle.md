# API Key Lifecycle and Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Task 4 API Key creation/listing/revocation/rotation, independent `X-API-Key` authentication, policy persistence/evaluation, admin-only policy management, and the specified tests without implementing Task 5 execution or quota behavior.

**Architecture:** Persist only a public prefix, versioned HMAC-SHA256 digest, and lifecycle metadata for each key. Management routes continue to use the existing JWT/session authentication, while public API dependencies read only `X-API-Key`; policy evaluation composes account/key state with an API-specific stored policy and returns a future-compatible decision without Redis or upstream execution. Rotation changes old/new rows in one database transaction so a failed commit rolls back the old-key revocation.

**Tech Stack:** FastAPI, SQLModel, PostgreSQL/SQLite test engines, Alembic, Pydantic, pytest, Ruff, Python 3.14, generated Hey API TypeScript client.

## Global Constraints

- Modify only the Task 4 files in `E:\AI_projects\yeyu-api\.git\sdd\task-4-brief.md`, plus generated client output and the listed tests.
- Never persist, log, print, or return a complete API secret except in the single create/rotate response object.
- Generate at least 32 random bytes with `secrets`, hash with versioned HMAC-SHA256 using the configured server pepper, and persist only digest/prefix/version/metadata.
- `/v1/*` authentication reads `X-API-Key` only; the management cookie must not authorize a public call.
- Unverified or inactive accounts and revoked keys are denied with the fixed `{ "error": { "code", "message", "request_id" } }` shape.
- Policy admin routes require the existing active-superuser dependency; normal users must receive 403.
- Do not implement Task 5 Redis quotas, tool execution, cache, or upstream adapters.
- Use the `yeyu-api` conda environment for Python commands and report PostgreSQL/Docker as unverified if unavailable.

---

### Task 1: Specify RED coverage for persistence and cryptographic lifecycle

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\tests\services\test_api_keys.py`
- Modify: `E:\AI_projects\yeyu-api\backend\tests\api\routes\test_api_keys.py`
- Modify: `E:\AI_projects\yeyu-api\backend\tests\api\routes\test_api_auth_boundary.py`
- Modify: `E:\AI_projects\yeyu-api\backend\tests\api\test_openapi_contract.py`

**Interfaces:**
- Tests consume the existing SQLModel SQLite fixture pattern and define the expected `ApiKeyService`, `CreatedApiKey`, `ApiKeyPrincipal`, policy decision, lifecycle routes, and OpenAPI security scheme.
- Tests produce the behavioral contract used by the implementation tasks; no complete secret is asserted in database/log output.

- [ ] **Step 1: Write service RED tests**

  Add tests for: a create result contains a secret while the `ApiKey` row contains no secret; HMAC digest changes with pepper/version; authenticate returns a principal for the active key; revoked authentication is distinguishable; list data has no `secret`; rotation exposes a new key and revokes the old key; a commit failure leaves the old key usable.

- [ ] **Step 2: Write route/auth RED tests**

  Add tests for create/list/revoke/rotate response wrappers, verified-account enforcement, exact error codes, ordinary-user denial of admin policy routes, management-cookie denial through the API-key dependency, and no complete secret in response after listing.

- [ ] **Step 3: Update OpenAPI RED expectations**

  Keep catalog assertions and add assertions that the API-key protected operation has an `XAPIKey`/`apiKey` security scheme with header name `X-API-Key`, while management routes remain bearer/session protected.

- [ ] **Step 4: Run only the listed Task 4 tests**

  Run:

  ```powershell
  conda run -n yeyu-api python -m pytest "E:\AI_projects\yeyu-api\backend\tests\services\test_api_keys.py" "E:\AI_projects\yeyu-api\backend\tests\api\routes\test_api_keys.py" "E:\AI_projects\yeyu-api\backend\tests\api\routes\test_api_auth_boundary.py" "E:\AI_projects\yeyu-api\backend\tests\api\test_openapi_contract.py" -q
  ```

  Expected: RED failure caused by missing Task 4 modules/routes/models, not a test collection or environment error.

---

### Task 2: Implement versioned key storage, security, migration, and user lifecycle routes

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\models.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\core\security.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\core\config.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\api\deps.py`
- Create: `E:\AI_projects\yeyu-api\backend\app\schemas\api_keys.py`
- Create: `E:\AI_projects\yeyu-api\backend\app\services\api_keys.py`
- Create: `E:\AI_projects\yeyu-api\backend\app\api\routes\api_keys.py`
- Create: `E:\AI_projects\yeyu-api\backend\app\alembic\versions\20261002_add_key_policy_tables.py`
- Modify: `E:\AI_projects\yeyu-api\backend\tests\services\test_api_keys.py`
- Modify: `E:\AI_projects\yeyu-api\backend\tests\api\routes\test_api_keys.py`

**Interfaces:**
- `ApiKeyService.create(user_id: UUID, label: str | None) -> CreatedApiKey`
- `ApiKeyService.authenticate(raw_key: str) -> ApiKeyPrincipal | None`
- `ApiKeyService.revoke(key_id: UUID, user_id: UUID) -> None`
- `ApiKeyService.rotate(key_id: UUID, user_id: UUID) -> CreatedApiKey`
- `get_api_key_principal(request: Request) -> ApiKeyPrincipal` with a database dependency, reading only the `X-API-Key` header.

- [ ] **Step 1: Add model and migration definitions**

  Add `ApiKey` with UUID, owner foreign key, prefix, HMAC digest, digest version, label, timestamps, `revoked_at`, and optional last-use metadata; add `ApiPolicy` keyed uniquely to `ApiDefinition`. Add the migration with `api_key` and `api_policy` tables, indexes, foreign keys, and data-loss guards on downgrade.

- [ ] **Step 2: Add cryptographic/configuration helpers**

  Add settings for current/previous pepper references and hash version, defaulting the current pepper reference to the existing persistent secret only for local compatibility. Add helpers that generate 32 random bytes, derive the public prefix, compute versioned HMAC-SHA256, and enumerate only explicitly configured pepper versions.

- [ ] **Step 3: Add schemas and service transaction behavior**

  Add create/list/response/error/principal schemas. Implement create/list/revoke/rotate; create and rotate commit only digest/prefix/metadata. Implement rotation as one transaction: set the old row revoked, add the new row, commit once, refresh the new row, and rollback on every failure so the old row remains valid.

- [ ] **Step 4: Add management routes and independent dependency**

  Register user-owned key routes under the existing API prefix. Management routes use `CurrentUser`; create/rotate reject unverified/inactive users. Add an `APIKeyHeader` OpenAPI dependency and structured error handling for missing, invalid, revoked, unverified, and suspended credentials. Do not inspect the management cookie in this dependency.

- [ ] **Step 5: Run service and route GREEN tests**

  Run the four listed Task 4 test files. Expected: all newly specified lifecycle and secrecy tests pass; if an assertion fails, fix production code rather than weakening the test.

---

### Task 3: Implement policy schema/service/admin boundary and route registration

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\models.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\api\main.py`
- Create: `E:\AI_projects\yeyu-api\backend\app\schemas\policy.py`
- Create: `E:\AI_projects\yeyu-api\backend\app\services\policy.py`
- Create: `E:\AI_projects\yeyu-api\backend\app\api\routes\admin_policies.py`
- Modify: `E:\AI_projects\yeyu-api\backend\tests\api\routes\test_api_auth_boundary.py`
- Modify: `E:\AI_projects\yeyu-api\backend\tests\api\test_openapi_contract.py`

**Interfaces:**
- `PolicyService.evaluate(principal: ApiKeyPrincipal, api: ApiDefinition, ip: IPvAnyAddress, now: datetime) -> PolicyDecision`
- `PolicyService.get(api_slug: str) -> PolicyView`
- `PolicyService.upsert(api_slug: str, payload: PolicyUpdate) -> PolicyView`
- `PolicyDecision` contains `allowed`, `reason`, `retry_after_seconds`, `daily_remaining`, and `minute_remaining`.

- [ ] **Step 1: Add policy schemas and evaluation tests**

  Cover allowed defaults, unverified account, inactive account, revoked key, disabled policy, and IP allowlist rejection. Keep rate/daily counters unimplemented; return configured limits as remaining capacity until Task 5 supplies atomic counters.

- [ ] **Step 2: Implement policy model/service**

  Persist enabled state, minute/daily/concurrency limits, and JSON IP allowlist; resolve by `ApiDefinition`; evaluate account/key state before policy state; never call Redis or an upstream.

- [ ] **Step 3: Implement admin-only policy routes**

  Add GET/PUT policy management under `/admin/policies/{api_slug}` with `get_current_active_superuser`. Ordinary users receive 403 and cannot infer or modify policy data.

- [ ] **Step 4: Register routes and run boundary/OpenAPI GREEN tests**

  Include `api_keys` and `admin_policies` in `app.api.main.api_router`, then run the listed Task 4 route and OpenAPI tests.

---

### Task 4: Full verification, generated client, review, and commit

**Files:**
- Generated only if the repository's OpenAPI client command changes tracked output: `E:\AI_projects\yeyu-api\frontend\src\client\*.gen.ts`
- Report: `E:\AI_projects\yeyu-api\.git\sdd\task-4-report.md`

- [ ] **Step 1: Run focused Task 4 tests in the `yeyu-api` conda environment.**
- [ ] **Step 2: Run Ruff on Task 4 app/tests/migration files and `python -m compileall` on `backend\app` and `backend\tests`.**
- [ ] **Step 3: Run OpenAPI generation/client TypeScript checks if the existing generator is available; do not claim PostgreSQL/Docker integration without a live service.**
- [ ] **Step 4: Review `git diff --check`, secret/search output, migration chain, and exact allowed changed paths.**
- [ ] **Step 5: Write the complete report with RED/GREEN evidence, verified/blocked/unverified boundaries, rollback concern, and commit hash.**
- [ ] **Step 6: Stage only Task 4 files, generated client output, tests, plan, and report; commit with `feat: add API key lifecycle and auth boundary`.**

## Self-Review Checklist

- [ ] Every production function introduced by Task 4 has a focused test or is a thin route/schema adapter covered by route/OpenAPI tests.
- [ ] RED output was observed before the corresponding implementation.
- [ ] No raw API secret appears in persisted columns, logs, generated output, test output, report, or Git diff.
- [ ] Rotation rollback behavior is tested with a failing commit and the result is reported explicitly.
- [ ] Cookie authentication is accepted only by management routes and never by `get_api_key_principal`.
- [ ] Task 5 execution, Redis quotas, cache, and upstream adapters remain absent.
