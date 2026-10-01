# Task 5 Quota and Cache Hardening Implementation Plan

> **For agentic workers:** Execute the steps in order with tests before production changes. Keep the existing `841fd63` behavior and unrelated worktree data intact.

**Goal:** Close the Task 5 quota/cache review findings with typed cache handles, validated cache time windows, one-time Redis admissions, safe concurrency TTLs, complete limit telemetry, guarded migration downgrade, and non-negative daily usage constraints.

**Architecture:** Keep Redis as the atomic minute/IP/concurrency primitive and PostgreSQL/SQLite as the authoritative daily usage store. In Redis mode, `PolicyService.evaluate()` performs the only minute/daily charge and attaches an opaque, service-owned admission handle to a private Pydantic attribute; `acquire()` validates and consumes that handle before acquiring only a concurrency lease. Cache low-level operations accept only factory-created `CacheKey` handles, while `*_for()` remains the normal slug/parameter entry point.

**Tech Stack:** Python 3.14, FastAPI/Pydantic, SQLModel/SQLAlchemy/Alembic, Redis Lua, pytest, Ruff.

## Global Constraints

- Use `conda run -n yeyu-api` for Python commands; never use conda `base` or Windows Store Python.
- Only modify the explicitly allowed backend models/schemas/services/migration and focused service tests, plus a narrowly necessary Redis/migration static test.
- Do not implement executors, adapters, public routes, trial pool, or frontend changes.
- Do not touch `E:\AI_projects\yeyubakahome_Web`, existing services, deployment, DNS, Nginx, or production data.
- Do not push; commit only after focused tests, Task 4 compatibility tests, Ruff, compileall, and diff checks pass.
- Do not print or log secrets or the opaque admission token.

---

### Task 1: Add RED tests for the review findings

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\tests\services\test_cache.py`
- Modify: `E:\AI_projects\yeyu-api\backend\tests\services\test_policy.py`
- Add if needed: `E:\AI_projects\yeyu-api\backend\tests\services\test_migrations.py`

- [ ] Add cache tests for future `data_at`, reversed timestamp order, a hand-written matching key, a tampered 2030 `stale_until`, service stale-age cap, and `stale_age=0` yielding `stale_until == expires_at`.
- [ ] Change cache test setup to use the typed factory handle and assert `CacheService.get/set/stale_value()` reject a raw matching string while `get_for/set_for/stale_value_for()` work.
- [ ] Add policy tests proving Redis `evaluate()` charges once, returns a private admission absent from `model_dump()`/JSON schema, and `acquire()` requires that admission, rejects forged/missing/expired/cross-principal/cross-API/cross-IP/reused decisions, and does not charge again.
- [ ] Extend the deterministic Redis fake to expose failure remaining values and model lease key TTL as the maximum member expiry; add tests for long-then-short and short-then-long leases.
- [ ] Add cleanup tests proving a release failure is raised when there is no original exception and cannot replace an original quota/adapter exception.
- [ ] Add migration/model tests proving both non-negative usage CHECK constraints are present and offline downgrade fails closed before DROP; preserve online empty-table/data behavior through static or in-memory evidence.
- [ ] Run the new focused tests before implementation and record the expected RED failures.

### Task 2: Harden cache time and key contracts

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\services\cache.py`

- [ ] Introduce a factory-only `CacheKey` handle with a private construction marker; make `build_cache_key()` and `CacheService.key_for()` return it, and make low-level `get/set/stale_value` require it.
- [ ] Keep slug validation, canonical parameter fingerprinting, and URL rejection; route `get_for/set_for/stale_value_for` through the factory.
- [ ] Parse Redis metadata defensively and validate `data_at <= expires_at <= stale_until`, `data_at <= now`, and `stale_until <= expires_at + self.max_stale_age_seconds` on every read.
- [ ] Define stale age after expiration: `stale_until = expires_at + min(requested_stale_age, configured_max_stale_age)`, including the zero-age boundary.
- [ ] Validate writes against the same invariant and reject future `data_at`; keep malformed/tampered Redis entries fail-closed as `CacheUnavailable` without returning stale data.

### Task 3: Enforce single-charge admission and cleanup boundaries

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\schemas\policy.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\services\policy.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\services\quota.py`

- [ ] Add a Pydantic private-only admission slot that is excluded from serialization/OpenAPI; keep public `PolicyDecision` fields unchanged.
- [ ] In Redis mode, create a service-owned opaque admission after successful minute/daily charging, bind it to principal IDs, API slug, IP, concurrency limit, and a short expiry, and retain no token in logs or response fields.
- [ ] Make Redis-mode `acquire()` reject missing, forged, expired, cross-context, and already-consumed admissions; atomically consume valid admissions and acquire only concurrency without invoking minute/daily charging.
- [ ] Preserve no-Redis `evaluate/get/upsert` static compatibility and keep denied decisions without admissions.
- [ ] Make `QuotaLease` release token-idempotent and ensure context-manager/policy cleanup raises cleanup errors when no original error exists but annotates and preserves an original error when one is active.

### Task 4: Fix Redis scripts and database invariants

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\services\redis.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\models.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\alembic\versions\20261003_add_usage_cache_tables.py`
- Modify: `E:\AI_projects\yeyu-api\backend\tests\services\test_policy.py`
- Add if needed: `E:\AI_projects\yeyu-api\backend\tests\services\test_migrations.py`

- [ ] Return failure `remaining_by_limit` after Lua rollback and parse it defensively while preserving the old deterministic one-value compatibility path.
- [ ] Set concurrency zset key expiry from the maximum current member score after every successful acquire, without changing token-level release semantics.
- [ ] Add named non-negative CHECK constraints for `request_count` and `weighted_units` in both SQLModel metadata and the Alembic create table.
- [ ] Make offline migration downgrade raise before emitting unconditional DROP SQL; retain online empty-table rollback and populated-table refusal.

### Task 5: Verify and commit

- [ ] Run the new cache/policy/Redis/migration focused tests, then the complete existing Task 4 policy tests.
- [ ] Run Ruff on changed Python files, `conda run -n yeyu-api python -m compileall` for backend app/tests, and `git diff --check`.
- [ ] Inspect the final diff and changed paths for scope/secret safety; record any standard conftest, PostgreSQL, Redis-server, or service-runtime blockers as real unverified scope.
- [ ] Commit with `fix: harden quota and cache contracts`; do not push.
