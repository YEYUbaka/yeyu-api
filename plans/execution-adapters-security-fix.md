# Execution Adapters Security Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the independent-review findings in the execution adapter and runner boundary without changing quota, cache, policy, route, model, database, or trial-pool code.

**Architecture:** Keep content providers opt-in and unregistered by default. The content adapter will resolve and validate every target hop, then call only an explicit `request_pinned` HTTP-client capability with the validated addresses and streaming enabled. `ApiRunner` will own one bounded executor per instance, and `ApiResponse` will become a strict Pydantic envelope whose public error fields are limited to safe data.

**Tech Stack:** Python 3.14, FastAPI/Pydantic 2, httpx-compatible synchronous adapters, pytest, Ruff, compileall.

## Global Constraints

- Project root is `E:\AI_projects\yeyu-api`; pushing is allowed only under the user's explicit public-repository authorization and after fresh verification.
- Only modify `backend\app\services\execution\adapters\content.py`, `backend\app\services\execution\runner.py`, `backend\app\services\execution\models.py`, `backend\tests\services\test_execution.py`, and execution-internal helper files if strictly necessary.
- Do not modify quota, cache, policy, routes, models, database, or trial-pool modules.
- Do not register a real content provider in the default `AdapterRegistry`.
- All tests use fake DNS/client/response objects and never access the public network.
- Run every RED command before its corresponding production implementation and record only real results.

---

### Task 1: Add failing security regression tests

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\tests\services\test_execution.py`

**Interfaces:**
- The fake HTTP client will expose `request_pinned(method, url, *, resolved_addresses, timeout, stream, follow_redirects)` and record the validated addresses and streaming flag.
- Tests will expect `ApiAdapter.validate_params`, `ApiRunner(max_workers=...)`, `ApiRunner.close()`, and an error envelope containing `code`, `message`, and `request_id`.

- [ ] **Step 1: Add RED tests for DNS pinning and target invariants.** Add tests that assert a validated public IPv4/IPv6 address reaches `request_pinned`, a generic-only client fails closed, endpoint port `:0` is rejected, metadata/loopback/link-local addresses are rejected, and an allowed-host redirect that changes the fixed path is rejected before a second request.
- [ ] **Step 2: Add RED tests for streamed bounded response handling.** Cover success, 3xx, 4xx, and 5xx bodies over the byte cap; assert `stream=True`, close/async-close invocation, long `Location` rejection, and a same-path redirect whose second hop is independently pinned.
- [ ] **Step 3: Add RED tests for runner admission and validation.** Use a slow adapter with `max_workers=1` to prove timed-out work retains the slot until its future completes, and use a cacheable adapter-specific validator to prove fresh-cache lookup happens only after validation. Strengthen every failure-envelope assertion with `message` and matching `request_id`.
- [ ] **Step 4: Add RED tests for strict response shape and default registry.** Assert `ApiResponse` rejects malformed/mixed error envelopes, preserves `to_dict`, `model_dump`, `[]`, and `get`, contains no stack/URL-secret/header fields, and that the default registry still contains only built-in tools.
- [ ] **Step 5: Run the focused tests and confirm expected failures.** Run `conda run -n yeyu-api pytest -q backend\tests\services\test_execution.py`; failures must be caused by the missing security behavior, not test collection or syntax errors.

### Task 2: Close content-adapter DNS, redirect, and response-lifecycle findings

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\services\execution\adapters\content.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\services\execution\models.py`

**Interfaces:**
- `AllowlistedHttpAdapter._validate_target()` returns the tuple of validated addresses.
- `AllowlistedHttpAdapter._request()` calls only `request_pinned(...)` or a callable explicitly marked with the same pinned contract; no generic `.request()` fallback is permitted.
- `ApiAdapter.validate_params()` provides bounded finite-JSON validation; content overrides it with its fixed parameter schema.

- [ ] **Step 1: Implement exact port/path checks and DNS result return.** Distinguish `parsed.port is None` from explicit `:0`; reject every port outside `1..65535`; enforce the fixed host, port, and path on the initial request and every redirect; reject unsafe IPv4, IPv6, hostname, and cloud-metadata targets; return only validated addresses for pinning.
- [ ] **Step 2: Implement the explicit pinned request contract.** Require `request_pinned` and pass the exact target, validated address tuple, remaining timeout, `stream=True`, and `follow_redirects=False`; return a safe upstream error when the injected client lacks that capability.
- [ ] **Step 3: Make every response read bounded and lifecycle-safe.** Read/discard response bytes for all statuses before branching, enforce `Content-Length` and streamed cumulative limits, enforce a byte limit on `Location`, parse JSON only from the already-bounded body, and close/async-close each response in `finally`, including redirects, errors, retries, and limit failures.
- [ ] **Step 4: Keep retry count and total deadline.** Preserve the existing finite retry policy and context deadline while ensuring a retry cannot bypass response closure or target revalidation.
- [ ] **Step 5: Run the focused adapter tests and refactor only after green.** Run `conda run -n yeyu-api pytest -q backend\tests\services\test_execution.py -k "http_adapter or endpoint or redirect or metadata or ipv6"` and inspect the fake-client call records.

### Task 3: Bound runner concurrency and harden error/cache flow

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\services\execution\runner.py`
- Modify: `E:\AI_projects\yeyu-api\backend\app\services\execution\models.py`

**Interfaces:**
- `ApiRunner.__init__(..., max_workers=8)` constructs one fixed `ThreadPoolExecutor` and bounded admission semaphore.
- `ApiRunner.close(wait=True, cancel_futures=True)` and `ApiRunner.shutdown(...)` close the instance executor.
- A submitted future releases its admission slot only from a done callback; timeout handling never releases it directly.

- [ ] **Step 1: Implement instance-level executor/admission.** Validate a finite worker count, submit only after bounded admission, attach exactly one done callback, and convert admission/submit failures to safe execution errors.
- [ ] **Step 2: Implement lifecycle methods.** Add idempotent `close`/`shutdown` behavior that marks the runner closed before executor shutdown and leaves already-running work governed by its future callback.
- [ ] **Step 3: Validate through the adapter before fresh-cache access.** Call `adapter.validate_params(params)`, require a mapping result, re-check the returned mapping at the generic JSON boundary, and only then call `_fresh_cache` or execute.
- [ ] **Step 4: Add request IDs to every failure error object.** Keep the public message from the `ExecutionError` class only, include `request_id` in `error` and `meta`, and never copy exception details, URLs, or response headers.
- [ ] **Step 5: Run runner tests and verify the slow-task slot behavior.** Run `conda run -n yeyu-api pytest -q backend\tests\services\test_execution.py -k "runner or cache or timeout"` and then the full focused file.

### Task 4: Replace `ApiResponse` with a strict compatible model

**Files:**
- Modify: `E:\AI_projects\yeyu-api\backend\app\services\execution\models.py`

**Interfaces:**
- `ApiResponse` remains constructible with `success`, `data`, `error`, and `meta`.
- `ApiResponse.to_dict()`, `model_dump()`, `__getitem__`, and `get()` retain the existing dictionary-facing behavior.
- Failed responses require `error.code`, `error.message`, and `error.request_id`; error keys are restricted to the safe public envelope.

- [ ] **Step 1: Implement a Pydantic 2 `BaseModel` with `extra="forbid"` and assignment validation.** Use strict success/error field checks and validate success/error consistency.
- [ ] **Step 2: Restrict public error content.** Reject missing request IDs, stack/traceback/exception fields, complete headers, URL-secret fields, and non-string public code/message values without serializing exception causes.
- [ ] **Step 3: Preserve dictionary compatibility.** Implement `to_dict`, `model_dump`, `__getitem__`, and `get` against the validated model and rerun all response-shape tests.

### Task 5: Full verification and delivery commit

**Files:**
- Verify only the allowed source/test files and the plan under `E:\AI_projects\yeyu-api\plans\`.

- [ ] **Step 1: Run focused and regression tests.** Run `conda run -n yeyu-api pytest -q backend\tests\services\test_execution.py` and the existing backend regression suite available in the project environment.
- [ ] **Step 2: Run static checks.** Run Ruff on the changed Python files, `python -m compileall` for `backend\app` and `backend\tests`, and `git diff --check`.
- [ ] **Step 3: Review the diff and scope.** Confirm no quota/cache/policy/routes/models/database/trial-pool files changed, no content provider was registered, no secrets or public-network calls were added, and no stack/URL/header data enters responses.
- [ ] **Step 4: Commit and push after review.** Create the fix commit, then push only after the final local review; the user has explicitly authorized pushing to `origin/main`.
- [ ] **Step 5: Report verification boundaries.** Explicitly separate verified local tests/static checks from unverified Docker, real-network, Redis, PostgreSQL, DNS, SMTP, OAuth, and production acceptance.

## Self-review checklist

- DNS validation output is consumed by an explicit pinned client capability on every hop.
- Unsupported clients fail closed and never receive a hostname through a generic request path.
- Success, redirect, 4xx, and 5xx response bodies are streamed, bounded, and closed.
- Port `:0`, IPv6, metadata addresses, and redirect path bypasses are covered.
- Timed-out runner tasks retain executor slots until their futures finish.
- Fresh cache is unreachable until adapter-specific validation succeeds.
- Every failed response has safe `code`, `message`, and `request_id` fields.
- `ApiResponse` dictionary compatibility is preserved.

## Fresh verification evidence (2026-10-02)

- The pre-fix isolated execution-module run produced 18 expected behavior failures and 19 passes; no syntax or collection error occurred in that isolated run.
- `conda run -n yeyu-api pytest -q --confcutdir="E:\AI_projects\yeyu-api\backend\tests\services" "E:\AI_projects\yeyu-api\backend\tests\services\test_execution.py"` → `37 passed` after the fix.
- Ruff on the four changed Python files → `All checks passed`.
- `conda run -n yeyu-api python -m compileall -q "E:\AI_projects\yeyu-api\backend\app" "E:\AI_projects\yeyu-api\backend\tests"` → exit code 0.
- `git diff --check` → no whitespace errors; only Git's LF/CRLF normalization warnings.
- The normal pytest collection path was attempted without injecting or printing settings values and failed during settings validation because required local variables were absent.
