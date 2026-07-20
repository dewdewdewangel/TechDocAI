# TechDoc AI Development Guide

This guide describes the supported local development, validation, and
troubleshooting workflows for TechDoc AI.

TechDoc AI currently targets local evaluation and small-scale testing.
Production-scale vector indexing, load testing, and a separate embedding
service remain planned work.

## Architecture overview

The local stack contains the following services:

- `db`: PostgreSQL with the pgvector extension
- `redis`: persistent document-processing queue
- `backend`: FastAPI application
- `worker`: Dramatiq document-processing worker
- `frontend`: React and Vite application
- `adminer`: local database administration interface
- `mailcatcher`: local email testing service
- `proxy`: local Traefik reverse proxy

Uploaded files are stored in the `app-upload-data` Docker volume. PostgreSQL,
Redis, and uploaded files must all be treated as persistent application data.

## Prerequisites

Install the following tools before starting development:

- Docker Desktop with Docker Compose
- Git
- Bun 1.3.12
- Python and uv for host-side backend validation

Verify the main tools:

```powershell
docker --version
docker compose version
bun --version
uv --version
```

## Environment configuration

TechDoc AI separates committed example configuration from local secrets:

- `.env.example` contains safe defaults and required variable names.
- `.env.local` contains local credentials and machine-specific paths.
- `.env.local` must never be committed.

Create `.env.local` only when it does not already exist:

```powershell
if (-not (Test-Path .env.local)) {
    Copy-Item .env.example .env.local
}
```

Do not overwrite an existing `.env.local`, because it may already contain a
valid local LLM API key or database configuration.

Review at least these variables:

- `SECRET_KEY`
- `FIRST_SUPERUSER`
- `FIRST_SUPERUSER_PASSWORD`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `BGE_MODEL_HOST_PATH`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

`BGE_MODEL_HOST_PATH` must point to the BGE-M3 model directory on the host
machine.

`EMBEDDING_MODEL_PATH` is the path inside the container and should normally
remain `/models/bge-m3`. Do not set it to a Windows drive path.

Never print API keys in terminal output, application logs, screenshots, issues,
or test reports.

## Start the complete stack

Run the following command from the repository root:

```powershell
docker compose `
  --env-file .env.example `
  --env-file .env.local `
  up -d --build
```

Docker Compose starts the database and Redis first, runs application startup
tasks, and then starts the API, worker, and frontend.

Check service status:

```powershell
docker compose `
  --env-file .env.example `
  --env-file .env.local `
  ps
```

All core services should be running or healthy.

## Local endpoints

The default development endpoints are:

- Frontend: <http://localhost:5173>
- Backend API: <http://localhost:8000>
- OpenAPI documentation: <http://localhost:8000/docs>
- Readiness check: <http://localhost:8000/api/v1/utils/health/ready>
- Prometheus metrics: <http://localhost:8000/metrics/>
- Adminer: <http://localhost:8080>
- Traefik dashboard: <http://localhost:8090>
- MailCatcher: <http://localhost:1080>

Check backend readiness from PowerShell:

```powershell
Invoke-WebRequest `
  http://localhost:8000/api/v1/utils/health/ready `
  -UseBasicParsing
```

A successful request should return an HTTP 200 response.

## View application logs

View backend and document-worker logs:

```powershell
docker compose `
  --env-file .env.example `
  --env-file .env.local `
  logs -f backend worker
```

Do not copy logs into public issues until they have been checked for local
paths, email addresses, document contents, and credentials.

Press `Ctrl+C` to stop following logs. This does not stop the containers.

## Frontend development

Install frontend dependencies from the repository root:

```powershell
bun install --frozen-lockfile
```

When the Compose frontend is running, it already occupies port 5173. Stop that
service before starting the Vite development server:

```powershell
docker compose `
  --env-file .env.example `
  --env-file .env.local `
  stop frontend

bun run dev
```

The host-side Vite server is then available at <http://localhost:5173>.

Run frontend validation from the repository root:

```powershell
bun run lint:check
bun run build
```

These commands use the `techdoc-ai-frontend` workspace configured in the root
`package.json`.

## Backend development

Install backend dependencies:

```powershell
Set-Location .\backend
uv sync
```

Run static analysis and tests:

```powershell
uv run ruff check app tests scripts
uv run mypy app
uv run ty check app
uv run pytest
```

Return to the repository root afterward:

```powershell
Set-Location ..
```

Backend tests should not require real production credentials. Tests must use
isolated configuration and must not send document content to an external LLM
unless the test is explicitly marked as an integration or evaluation test.

## Database migrations

The normal Compose startup process runs the existing migrations.

To inspect the current migration heads:

```powershell
Set-Location .\backend
uv run alembic heads
Set-Location ..
```

To apply migrations inside the running backend container:

```powershell
docker compose `
  --env-file .env.example `
  --env-file .env.local `
  exec backend alembic upgrade head
```

New schema changes must include a reviewed Alembic migration. Do not edit an
already published migration merely to hide a later schema change.

## Document-processing workflow

When a user uploads a document:

1. The API stores the upload metadata and queues a processing job.
2. The worker claims the job.
3. The document is parsed and split into chunks.
4. BGE-M3 generates embeddings.
5. The chunks and embeddings are stored in PostgreSQL with pgvector.
6. The document status becomes indexed or failed.

If a document remains queued, inspect both Redis and worker status:

```powershell
docker compose `
  --env-file .env.example `
  --env-file .env.local `
  ps redis worker

docker compose `
  --env-file .env.example `
  --env-file .env.local `
  logs --tail 100 worker
```

## End-to-end tests

Start the complete stack before running Playwright:

```powershell
bun run test
```

The real document-to-LLM workflow is opt-in because it consumes embedding
resources and LLM quota:

```powershell
$env:RUN_RAG_E2E = "1"
$env:PLAYWRIGHT_CHANNEL = "chrome"

Set-Location .\frontend
bunx playwright test tests/techdoc-flow.spec.ts --project=chromium
Set-Location ..
```

Remove the temporary environment variables after the test:

```powershell
Remove-Item Env:RUN_RAG_E2E -ErrorAction SilentlyContinue
Remove-Item Env:PLAYWRIGHT_CHANNEL -ErrorAction SilentlyContinue
```

Do not enable this test with a billable API key unless the expected cost and
test data have been reviewed.

## RAG evaluation

After uploading and indexing the evaluation documents, run:

```powershell
Set-Location .\backend
uv run python scripts/evaluate_rag.py --user-email your-user@example.com
Set-Location ..
```

Evaluation reports include retrieval and citation metrics. Evaluation data
must not contain confidential production documents.

## Stop the environment

Stop containers while retaining persistent volumes:

```powershell
docker compose `
  --env-file .env.example `
  --env-file .env.local `
  down
```

Do not add `--volumes` unless the PostgreSQL, Redis, and uploaded-file data may
safely be deleted.

## Troubleshooting

### Port already in use

Check whether ports 5173, 8000, 5432, 6379, 8080, 8090, or 1080 are already
being used by another local process.

### Backend is not ready

Inspect the database, Redis, startup, and backend services:

```powershell
docker compose `
  --env-file .env.example `
  --env-file .env.local `
  ps db redis prestart backend

docker compose `
  --env-file .env.example `
  --env-file .env.local `
  logs --tail 100 prestart backend
```

### Embedding model cannot be loaded

Verify that `BGE_MODEL_HOST_PATH` points to a complete local BGE-M3 model
directory and that Docker Desktop can access that host path.

### Chat requests fail

Verify `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` in `.env.local`. Do not
paste the API key into diagnostic commands or issue reports.

### Document remains queued

Verify that Redis and the worker are running, then inspect worker logs. Restart
the worker only after preserving the relevant error output:

```powershell
docker compose `
  --env-file .env.example `
  --env-file .env.local `
  restart worker
```

## Development security rules

- Never commit `.env` or `.env.local`.
- Never use production documents as public test fixtures.
- Never include API keys in screenshots, logs, commits, or issues.
- Keep uploaded documents owner-scoped.
- Review generated OpenAPI clients before committing them.
- Run the secret scanner before every publication candidate.