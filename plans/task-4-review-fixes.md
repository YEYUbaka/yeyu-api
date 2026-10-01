# Task 4 Review Fixes Implementation Plan

> **For agentic workers:** Execute the steps in order with tests before production changes. Keep the existing `9db9ceb` implementation and unrelated worktree data intact.

**Goal:** Close all six independent-review findings for Task 4 API-key security, migration safety, lifecycle transaction behavior, application-wide errors, OpenAPI/client contracts, and policy IP validation.

**Architecture:** Keep API-key authentication independent from management cookies. Make configuration validation reject unsafe production pepper states at startup and make the hash helper consume only validated current/previous pepper pairs. Register one FastAPI application handler for `ApiError`, keep route dependencies ordinary, build create/rotate response DTOs from in-memory fields before commit, and validate/normalize IP networks at the Pydantic input boundary.

**Tech Stack:** FastAPI, Pydantic Settings, SQLModel/Alembic, pytest, Ruff, compileall, GitHub Actions, Hey API OpenAPI client, pnpm/TypeScript.

## Global Constraints

- Use the `yeyu-api` conda environment for Python commands; never use conda `base` or Windows Store Python.
- Do not touch `E:\AI_projects\yeyubakahome_Web`, existing services, servers, DNS, Nginx, or production data.
- Do not reset, delete, or rewrite existing commits; do not push.
- Do not print complete API keys, peppers, passwords, OAuth values, or other credentials.
- Keep `.env.example` limited to placeholders and mask CI pepper values with GitHub Actions `::add-mask::`.
- Distinguish local verification from blocked/not-verified PostgreSQL and Docker checks.

---

### Task 1: Add RED coverage for all review findings

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\tests\services\test_api_keys.py`
- Modify: `E:\AI_projects\yeyu-api\backend\tests\api\routes\test_api_auth_boundary.py`
- Modify: `E:\AI_projects\yeyu-api\backend\tests\api\routes\test_api_keys.py`
- Modify: `E:\AI_projects\yeyu-api\backend\tests\api\test_openapi_contract.py`
- Modify: `E:\AI_projects\yeyu-api\backend\tests\services\test_api_keys.py`

- [ ] Add config tests proving production without an independent `API_KEY_PEPPER` fails closed, valid current/previous pairs are accepted, incomplete pairs and invalid/non-positive/equal versions fail, and hash helpers never fall back to `SECRET_KEY`.
- [ ] Add a migration test that renders offline downgrade SQL and asserts the generated SQL contains a database-side non-empty guard before either `DROP TABLE`, or rejects offline generation safely.
- [ ] Add a narrow service test that makes `Session.refresh` fail after a successful commit and proves create/rotate still return the in-memory secret response and preserve lifecycle state.
- [ ] Change the auth probe to a normal `APIRouter` without `ApiErrorRoute`; assert missing and invalid API keys have the exact `{error: {code, message, request_id}}` envelope.
- [ ] Add OpenAPI assertions for fixed `ApiErrorResponse` responses on every API-key-protected operation and generated client error types for 401/403 where applicable.
- [ ] Add route tests for invalid and non-canonical `allowed_ips`, asserting 422 and canonical `ip_network(..., strict=False)` output for valid input.
- [ ] Run each new focused test before implementation and record the expected RED failures without changing the assertions to fit the current code.

### Task 2: Implement fail-closed pepper configuration and CI setup

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\core\config.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\core\security.py`
- Modify: `E:\AI_projects\yeyu-api\.env.example`
- Modify: `E:\AI_projects\yeyu-api\.github\workflows\test-backend.yml`
- Modify: `E:\AI_projects\yeyu-api\.github\workflows\playwright.yml`
- Modify: `E:\AI_projects\yeyu-api\.github\workflows\test-docker-compose.yml` if it runs the backend with key hashing

- [ ] Require a non-empty independent current `API_KEY_PEPPER` outside development; reject the old `SECRET_KEY` fallback.
- [ ] Validate current version as a positive integer, previous pepper/version as an all-or-none pair, and require a positive previous version different from current.
- [ ] Make `_api_key_pepper`, `api_key_hash_versions`, and hashing helpers use only validated explicit pepper values.
- [ ] Add only placeholder values and comments to `.env.example`.
- [ ] Generate a random CI-only pepper in each relevant workflow, expose it only through the step environment, and immediately emit `::add-mask::` without echoing the value.

### Task 3: Implement offline migration protection and in-memory lifecycle responses

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\alembic\versions\20261002_add_key_policy_tables.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\services\api_keys.py`

- [ ] Make downgrade protection apply in offline mode using PostgreSQL `DO $$` guards that check row counts and raise before drops; retain online protection and ensure the SQL is PostgreSQL-specific rather than an unconditional drop.
- [ ] Construct `CreatedApiKey` after fields are generated and before commit; on commit failure rollback and re-raise; remove post-commit `refresh` from create and rotate so a refresh failure cannot invalidate a successful operation.
- [ ] Keep rotation atomic: commit only once, with old revocation and replacement insert in the same transaction; no response path may read the database after commit.

### Task 4: Register global ApiError handling, validate policy input, and regenerate contracts

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\main.py` or the application factory module
- Modify: `E:\AI_projects\yeyu-api\backend\app\api\deps.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\api\routes\api_keys.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\schemas\policy.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\api\routes\admin_policies.py` if response declarations are needed
- Regenerate only: `E:\AI_projects\yeyu-api\frontend\src\client\index.ts`, `sdk.gen.ts`, `types.gen.ts`

- [ ] Register an application-level `ApiError` exception handler returning the fixed envelope and remove the route-class dependency from ordinary routes/probes.
- [ ] Declare `ApiErrorResponse` for 401/403 (and relevant fixed API-key errors) in protected route `responses` so OpenAPI and generated client types include the envelope.
- [ ] Parse every `allowed_ips` entry as an IP address/network with `strict=False`, store canonical strings, and raise validation errors for invalid entries; leave policy-service historical bad-value handling fail-closed.
- [ ] Regenerate the frontend client from the updated OpenAPI document and run TypeScript checking.

### Task 5: Full verification, report, and commit

- [ ] Run the four required Task 4 backend test files plus the new config/migration tests in `conda run -n yeyu-api`.
- [ ] Run Ruff and `python -m compileall` for backend app/tests.
- [ ] Run OpenAPI client generation and `tsc --noEmit`.
- [ ] Inspect `git diff --check`, secret-safe diff/search results, and changed paths; do not include `.playwright-mcp` or unrelated files.
- [ ] Append a detailed evidence-bounded report to `E:\AI_projects\yeyu-api\.git\sdd\task-4-report.md`, including RED/GREEN commands, blocked/not-verified PostgreSQL/Docker scope, and no secret values.
- [ ] Commit the verified changes with `fix: close task 4 security review findings`; do not push.
