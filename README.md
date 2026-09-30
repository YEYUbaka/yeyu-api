# Yeyu API

[![Test Docker Compose](../../actions/workflows/test-docker-compose.yml/badge.svg)](../../actions/workflows/test-docker-compose.yml)
[![Test Backend](../../actions/workflows/test-backend.yml/badge.svg)](../../actions/workflows/test-backend.yml)

Yeyu API 是独立的公益 API 聚合平台。本仓库当前处于 Task 1 框架基线阶段，业务域仍按后续任务边界逐步替换官方模板示例。

官方 Full Stack FastAPI Template 的固定来源、准确 commit、许可证、导入边界和验证记录见 [`docs/framework-baseline.md`](./docs/framework-baseline.md)。

## Technology Stack and Features

- ⚡ [**FastAPI**](https://fastapi.tiangolo.com) for the Python backend API.
  - 🧰 [SQLModel](https://sqlmodel.tiangolo.com) for the Python SQL database interactions (ORM).
  - 🔍 [Pydantic](https://docs.pydantic.dev), used by FastAPI, for the data validation and settings management.
  - 💾 [PostgreSQL](https://www.postgresql.org) as the SQL database.
- 🚀 [React](https://react.dev) for the frontend.
  - 🧩 Built into the backend application and served by FastAPI on the same domain as the API.
  - 💃 Using TypeScript, hooks, [Vite](https://vitejs.dev), and other parts of a modern frontend stack.
  - 🎨 [Tailwind CSS](https://tailwindcss.com) and [shadcn/ui](https://ui.shadcn.com) for the frontend components.
  - 🤖 An automatically generated frontend client.
  - 🧪 [Playwright](https://playwright.dev) for end-to-end testing.
  - 🦇 Dark mode support.
- 🐋 [Docker Compose](https://www.docker.com) for local development and integration services.
  - 📞 [Traefik](https://traefik.io) as a local reverse proxy.
- 🔒 Secure password hashing by default.
- 🔑 JWT (JSON Web Token) authentication.
- 📫 Email-based password recovery.
- ✉️ [React Email](https://react.email) for email templates.
- 📬 [Mailpit](https://mailpit.axllent.org) for local email testing during development.
- ✅ Tests with [Pytest](https://pytest.org).
- 🏭 CI (continuous integration) based on GitHub Actions.

## Local Baseline

使用项目独立的 conda 环境和 pnpm 入口，不使用 conda base 或 Windows Store Python。

```powershell
conda run -n yeyu-api python -m pytest E:\AI_projects\yeyu-api\backend\tests -q
pnpm --dir E:\AI_projects\yeyu-api\frontend run build
pnpm --dir E:\AI_projects\yeyu-api\frontend exec playwright test
```

Docker Compose 仅作为本地集成栈入口；如果本机没有 Docker，只记录为未验证，不安装 Docker 或触碰线上服务。

## Backend Development

Backend docs: [backend/README.md](./backend/README.md).

## Frontend Development

Frontend docs: [frontend/README.md](./frontend/README.md).

## Development

General development docs: [development.md](./development.md).

This includes the local FastAPI and Vite workflow, Docker Compose services, `.env` configuration, and more.

## License

The Full Stack FastAPI Template is licensed under the terms of the MIT license.
