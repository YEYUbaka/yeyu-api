# FastAPI Project - Development

## Local Development

For local development, run PostgreSQL and Mailpit with Docker Compose, and run the FastAPI and Vite development servers locally.

For the first setup, create the project conda environment and install the hash-locked Python dependencies. The root uv.lock remains the dependency lock/source record.

~~~bash
conda create -n yeyu-api python=3.14 -y
conda activate yeyu-api
python -m pip install --require-hashes --requirement backend/requirements-dev.lock.txt
python -m pip install --require-hashes "prek==0.4.14" --hash=sha256:f6d0952e31ffd6e508660749dd51b8d8de96e955ed12c40e411f3224f502fed2 --hash=sha256:29364012d5704475d1092eb8a96ea30b163279096ad5e0c80a620fffa79bc639
~~~

Start the supporting services:

```bash
docker compose up -d db mailpit
```

Then, from the `backend` directory, install the dependencies and prepare the database:

```bash
conda activate yeyu-api
bash scripts/prestart.sh
```

Start the FastAPI development server:

```bash
conda activate yeyu-api
python -m fastapi dev
```

In another terminal, from the project root, install the frontend dependencies and start the Vite development server:

~~~bash
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend run dev
~~~

Now you can open these URLs:

Frontend development server: <http://localhost:5173>

Backend API: <http://localhost:8000>

Automatic interactive API documentation with Swagger UI: <http://localhost:8000/docs>

Mailpit: <http://localhost:8025>

The frontend development server uses the backend at `http://localhost:8000`, as configured in `frontend/.env`.

### Frontend Served by FastAPI

Build the frontend from the `frontend` directory:

~~~bash
pnpm --dir frontend run build
~~~

The build is written to `backend/app/frontend` and served by FastAPI at <http://localhost:8000>. Rebuild the frontend after making frontend changes.

## Full Stack with Docker Compose

To run the backend and built frontend in Docker Compose:

```bash
docker compose run --rm backend bash scripts/prestart.sh
docker compose watch
```

Now you can open these URLs:

Application, with the frontend and API served by FastAPI: <http://localhost:8000>

Automatic interactive API documentation with Swagger UI: <http://localhost:8000/docs>

Adminer, database web administration: <http://localhost:8080>

Traefik UI, to see how the routes are being handled by the proxy: <http://localhost:8090>

Mailpit: <http://localhost:8025>

Stop a locally running FastAPI server before starting the Compose backend because both use port `8000`.

**Note**: The first time you start the stack, it might take a minute for all the services to be ready. To monitor it, use `docker compose logs`, or `docker compose logs backend` for the backend service.

## Mailpit

[Mailpit](https://mailpit.axllent.org) captures emails sent during local development instead of delivering them. The local backend connects to it at `localhost:1025`, and the Compose backend connects to the `mailpit` service. Captured emails are available at <http://localhost:8025>.

## Docker Compose Files and Environment Variables

The main `compose.yml` file contains the configuration shared by the whole stack. Docker Compose loads it automatically.

The `compose.override.yml` file adds local development settings, such as mounting the source code as a volume. Docker Compose also loads it automatically and applies it on top of `compose.yml`.

The backend reads local settings from the `.env` file. Docker Compose also uses it for variable interpolation and passes the settings each container needs.

After changing variables, make sure you restart the stack:

```bash
docker compose watch
```

## The `.env` File

The local `.env` file contains development-only values and must remain untracked. Its hostnames use `localhost` for processes running on your machine. Docker Compose overrides hostnames such as the database and SMTP server with their Compose service names.

Do not store real secrets in the repository. Use the local `.env.example` as the variable reference and keep the actual `.env` file untracked.

## Pre-commit Hooks and Code Linting

The project uses [prek](https://prek.j178.dev/), a modern alternative to [pre-commit](https://pre-commit.com/), for code linting and formatting.

You can find a file `.pre-commit-config.yaml` with configurations at the root of the project.

### Install `prek` to Run Automatically

`prek` is already part of the dependencies of the project.

From the project root, install the Git hook so that `prek` runs automatically before each commit:

```bash
conda activate yeyu-api
prek install -f
```

The `-f` flag forces the installation, in case there was already a `pre-commit` hook previously installed.

Now whenever you try to commit, for example with:

```bash
git commit
```

`prek` will check and format the code you are about to commit. If it modifies any files, add those files to Git again before committing.

### Run `prek` Manually

You can also run `prek` manually on all files from the project root:

```bash
conda activate yeyu-api
prek run --all-files
```
