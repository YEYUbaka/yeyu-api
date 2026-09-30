# Task 1 Review Fixes Implementation Plan

> For agentic workers: execute this plan inline with the current user-authorized workspace. Steps use checkbox syntax for tracking.

Goal: 修复 Task 1 审查指出的 GitHub Actions Compose 环境变量、GitHub context 泄露、conda 本地开发入口和生成文件行尾空白问题，并提交一个可审计的本地修复提交。

Architecture: 在三个实际运行 Compose 的 GitHub Actions job 中，各加入一个 Bash 步骤，在 runner 上用 openssl rand -hex 32 生成临时密码/密钥并只追加到 GITHUB_ENV；非敏感 CI 配置使用 .test 邮箱、localhost 和 Mailpit 端口。保留自动加载的 compose.override.yml，使 mailpit 和 playwright 服务继续由 override 提供。文档只把 Python 本地入口切换为已有的 yeyu-api conda 环境，并保留 uv.lock 作为锁定来源说明。

Tech Stack: GitHub Actions YAML, Docker Compose, Bash, Conda yeyu-api, Markdown, PowerShell static checks, Git.

## Global Constraints

- 只修改 E:\AI_projects\yeyu-api，不触碰 E:\AI_projects\yeyubakahome_Web、new.api.yeyubaka.top、服务器、DNS、Nginx。
- 不写入任何真实密码、token、API key、SMTP 凭据或其他 secret；CI secret/password 必须在 runner 运行时生成。
- compose.yml 的 POSTGRES_PASSWORD、PROJECT_NAME、SECRET_KEY、FIRST_SUPERUSER、FIRST_SUPERUSER_PASSWORD、EMAILS_FROM_EMAIL 必须在三个目标 workflow 的 Compose job 中从 GITHUB_ENV 得到值。
- pre-commit.yml 不得输出完整 github 对象；toJSON(needs) 的 job 状态汇总保持不变。
- 本地 Python 运行入口只能使用 conda 环境 yeyu-api，三个指定文档中不得保留 uv run 或 .venv 入口。
- 不升级模板镜像或 astral-sh/setup-uv action；只记录其版本固定性作为后续任务。
- 不声称 Docker/Compose、pytest、前端 build 或浏览器 E2E 通过，除非本轮实际执行并取得对应退出码 0。

---

### Task 1: Add runtime-only Compose environment to CI

Files:
- Modify: E:\AI_projects\yeyu-api\.github\workflows\test-backend.yml
- Modify: E:\AI_projects\yeyu-api\.github\workflows\test-docker-compose.yml
- Modify: E:\AI_projects\yeyu-api\.github\workflows\playwright.yml
- Read-only contract: E:\AI_projects\yeyu-api\compose.yml, E:\AI_projects\yeyu-api\compose.override.yml

Interfaces:
- Consumes: GitHub runner Bash, openssl, the per-job GITHUB_ENV file, and Compose interpolation in compose.yml.
- Produces: POSTGRES_PASSWORD, PROJECT_NAME, SECRET_KEY, FIRST_SUPERUSER, FIRST_SUPERUSER_PASSWORD, EMAILS_FROM_EMAIL, SMTP_HOST, SMTP_PORT, SMTP_TLS, SMTP_USER, SMTP_PASSWORD, DOMAIN, DATABASE_URL, VITE_API_URL, MAILPIT_HOST, and SENTRY_DSN for later steps in each Compose job.

- [ ] Step 1: Run the red static contract check

Run from E:\AI_projects\yeyu-api:

~~~powershell
$required = @('POSTGRES_PASSWORD','PROJECT_NAME','SECRET_KEY','FIRST_SUPERUSER','FIRST_SUPERUSER_PASSWORD','EMAILS_FROM_EMAIL')
$workflowPaths = @('E:\AI_projects\yeyu-api\.github\workflows\test-backend.yml','E:\AI_projects\yeyu-api\.github\workflows\test-docker-compose.yml','E:\AI_projects\yeyu-api\.github\workflows\playwright.yml')
$workflowText = ($workflowPaths | ForEach-Object { Get-Content -Raw -LiteralPath $_ }) -join ([Environment]::NewLine)
foreach ($name in $required) { if ($workflowText -notmatch [regex]::Escape("printf '$name=")) { exit 1 } }
~~~

Expected: non-zero because the runtime environment step does not exist yet.

- [ ] Step 2: Add the runtime-generated environment step to each Compose workflow

Insert after checkout in each Compose-running job:

~~~yaml
- name: Configure temporary test environment
  shell: bash
  run: |
    set -euo pipefail
    ci_postgres_password="$(openssl rand -hex 32)"
    ci_secret_key="$(openssl rand -hex 32)"
    ci_superuser_password="$(openssl rand -hex 32)"
    {
      printf 'POSTGRES_PASSWORD=%s\n' "$ci_postgres_password"
      printf 'PROJECT_NAME=Yeyu API CI\n'
      printf 'SECRET_KEY=%s\n' "$ci_secret_key"
      printf 'FIRST_SUPERUSER=ci-admin@example.test\n'
      printf 'FIRST_SUPERUSER_PASSWORD=%s\n' "$ci_superuser_password"
      printf 'EMAILS_FROM_EMAIL=ci-admin@example.test\n'
      printf 'SMTP_HOST=localhost\n'
      printf 'SMTP_PORT=1025\n'
      printf 'SMTP_TLS=false\n'
      printf 'SMTP_USER=\n'
      printf 'SMTP_PASSWORD=\n'
      printf 'DOMAIN=localhost\n'
      printf 'DATABASE_URL=postgresql://postgres:%s@localhost:5432/app\n' "$ci_postgres_password"
      printf 'VITE_API_URL=http://localhost:8000\n'
      printf 'MAILPIT_HOST=http://localhost:8025\n'
      printf 'SENTRY_DSN=\n'
    } >> "$GITHUB_ENV"
~~~

The step must not echo generated variables. The existing Compose commands remain unchanged so the repository's automatic override loading continues to provide mailpit and playwright.

- [ ] Step 3: Verify the workflow contract statically

Run:

~~~powershell
rg -n 'Configure temporary test environment|GITHUB_ENV|openssl rand -hex 32|POSTGRES_PASSWORD|PROJECT_NAME|SECRET_KEY|FIRST_SUPERUSER|FIRST_SUPERUSER_PASSWORD|EMAILS_FROM_EMAIL|SMTP_HOST|DOMAIN' 'E:\AI_projects\yeyu-api\.github\workflows\test-backend.yml' 'E:\AI_projects\yeyu-api\.github\workflows\test-docker-compose.yml' 'E:\AI_projects\yeyu-api\.github\workflows\playwright.yml'
rg -n 'mailpit:|playwright:|dockerfile: frontend/Dockerfile.playwright' 'E:\AI_projects\yeyu-api\compose.override.yml'
~~~

Expected: all three workflow files contain the runtime step and required variables; the override contains both services and the Playwright Dockerfile.

### Task 2: Remove GitHub context dump and update local Python documentation

Files:
- Modify: E:\AI_projects\yeyu-api\.github\workflows\pre-commit.yml
- Modify: E:\AI_projects\yeyu-api\backend\README.md
- Modify: E:\AI_projects\yeyu-api\development.md
- Modify: E:\AI_projects\yeyu-api\frontend\README.md
- Modify: E:\AI_projects\yeyu-api\frontend\src\client\sdk.gen.ts

Interfaces:
- Consumes: existing uv.lock, backend\pyproject.toml, and conda environment name yeyu-api.
- Produces: executable local instructions using conda activate yeyu-api and concrete python -m fastapi/python -m alembic commands; no uv run or .venv local entry in the three documents.

- [ ] Step 1: Run the red documentation and exposure checks

Run:

~~~powershell
rg -n 'toJson\(github\)|uv run|\.venv' 'E:\AI_projects\yeyu-api\.github\workflows\pre-commit.yml' 'E:\AI_projects\yeyu-api\backend\README.md' 'E:\AI_projects\yeyu-api\development.md' 'E:\AI_projects\yeyu-api\frontend\README.md'
~~~

Expected: the command finds the known review findings before the fix.

- [ ] Step 2: Delete only the Dump GitHub context step

Keep the re-actors/alls-green step and its toJSON(needs) job-status input; remove the step that assigns the GITHUB_CONTEXT environment variable from the full github object and echoes it.

- [ ] Step 3: Convert the three local Python entry points to conda

Use this executable setup from the project root:

~~~console
conda create -n yeyu-api python=3.14 -y
conda activate yeyu-api
python -m pip install --require-hashes --requirement backend\requirements-dev.lock.txt
~~~

Then use conda activate yeyu-api followed by python -m fastapi, bash scripts/prestart.sh, bash scripts/test.sh, python -m alembic, and prek as appropriate for the existing documented commands. Install prek at the fixed version/hash recorded in uv.lock before using its command. Explain that root uv.lock remains the dependency-locking/source record; do not present uv run or .venv as a local Python entry.

- [ ] Step 4: Remove generated-file trailing whitespace

Strip only line-ending spaces and tabs from E:\AI_projects\yeyu-api\frontend\src\client\sdk.gen.ts, preserving all code content and line endings.

### Task 3: Record evidence, verify, and commit

Files:
- Modify: E:\AI_projects\yeyu-api\.git\sdd\task-1-report.md

- [ ] Step 1: Run the requested static checks

Run fresh commands for git diff --check, absence of the full github context expression in workflows, absence of uv run/.venv in the three documents, secret-pattern scans, Compose-expression/runtime-env coverage, and git status --short.

- [ ] Step 2: Append Fix 3 结果 to the Task 1 report

Record each real command and exit code, the modified files, the Compose override evidence, the fact that generated values were not printed or committed, and the fact that Docker/Compose/pytest/frontend build were not claimed as passing. Record unresolved follow-up only for template image and astral-sh/setup-uv action version pinning.

- [ ] Step 3: Commit the scoped changes

Run:

~~~powershell
git -C 'E:\AI_projects\yeyu-api' diff --check
git -C 'E:\AI_projects\yeyu-api' status --short
git -C 'E:\AI_projects\yeyu-api' add -- '.github/workflows/test-backend.yml' '.github/workflows/test-docker-compose.yml' '.github/workflows/playwright.yml' '.github/workflows/pre-commit.yml' 'backend/README.md' 'development.md' 'frontend/README.md' 'frontend/src/client/sdk.gen.ts'
git -C 'E:\AI_projects\yeyu-api' commit -m 'fix: address task 1 review findings'
~~~

Expected: the commit succeeds with exactly the requested message; do not push.
