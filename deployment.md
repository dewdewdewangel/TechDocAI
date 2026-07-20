# TechDoc AI Deployment Guide

This guide describes the deployment contract currently supported by TechDoc AI.
The repository provides CI checks, container build definitions, migrations, and
Docker Compose configuration. It does not currently provide automatic staging
or production deployment.

TechDoc AI is an active MVP intended for local evaluation and small-scale
deployments. Production-scale vector indexing, load testing, and a dedicated
embedding service remain planned work.

## Architecture

A complete deployment contains:

- PostgreSQL with pgvector
- Redis with append-only persistence
- the FastAPI backend
- one Dramatiq document worker
- the React frontend
- persistent uploaded-file storage
- an external reverse proxy that terminates TLS

The backend and worker both load BGE-M3 in-process. Keep each at one process
with the current architecture. Before horizontal scaling, move embeddings to a
dedicated service or verify the resulting memory use under production load.

## Automation boundary

The workflows under `.github/workflows` validate the frontend, backend, Actions
configuration, and secret history. They do not publish images, access a server,
change infrastructure, or deploy an environment.

Choose and review a target platform before adding continuous deployment.
Production credentials must be stored by that platform and must not be
committed to this repository.

## Required infrastructure

For the provided single-host Compose deployment, prepare:

- a Linux host with Docker Engine and Docker Compose
- enough memory for the API, worker, and two BGE-M3 model instances
- persistent storage for PostgreSQL, Redis, and uploaded documents
- DNS names for the frontend and API
- an external `traefik-public` Docker network
- a reverse proxy with HTTPS certificate management
- a backup target outside the application host

The base `compose.yml` expects the reverse proxy and `traefik-public` network to
be managed outside this repository. The proxy in `compose.override.yml` is for
local development and is not the production TLS endpoint.

Create the external network once when required:

```bash
docker network inspect traefik-public >/dev/null 2>&1 || \
  docker network create traefik-public
```

## Production configuration

Use `.env.example` only as a list of variable names and safe defaults. Store
real values in the deployment platform secret manager. A manually managed host
may use a non-committed `.env.local` only when access is restricted to the
deployment account.

Review and set at least:

- `DOMAIN` and `ENVIRONMENT=production`
- `FRONTEND_HOST` and `BACKEND_CORS_ORIGINS`
- `SECRET_KEY`
- `FIRST_SUPERUSER` and `FIRST_SUPERUSER_PASSWORD`
- `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`
- `BGE_MODEL_HOST_PATH`
- `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`
- `SENTRY_DSN`
- `DOCKER_IMAGE_BACKEND`, `DOCKER_IMAGE_FRONTEND`, and `TAG`

Use unique application and database secrets. Never deploy the placeholders
from `.env.example`.

`BGE_MODEL_HOST_PATH` must be an absolute host path containing a verified
BGE-M3 model. Compose mounts it read-only at `/models/bge-m3`. Do not store
credentials or confidential documents in that directory.

## Validate and start

Validate interpolation without publishing the rendered configuration:

```bash
docker compose \
  --env-file .env.example \
  --env-file .env.local \
  -f compose.yml config --quiet
```

Do not attach expanded Compose output to an issue because it may contain
secrets.

Start or update the stack:

```bash
docker compose \
  --env-file .env.example \
  --env-file .env.local \
  -f compose.yml up -d --build
```

The one-shot `prestart` service waits for PostgreSQL, applies Alembic
migrations, and creates the initial administrator before the API and worker
start.

Inspect service state and recent logs:

```bash
docker compose --env-file .env.example --env-file .env.local -f compose.yml ps
docker compose --env-file .env.example --env-file .env.local -f compose.yml \
  logs --tail 100 backend worker
```

Review logs for email addresses, paths, document content, and credentials
before sharing them outside the operations team.

## Database migrations

Migrations run during normal Compose startup. Before an update, review pending
Alembic revisions and confirm that the database backup is restorable.

To run the startup and migration task explicitly:

```bash
docker compose --env-file .env.example --env-file .env.local -f compose.yml \
  run --rm prestart
```

Do not edit an already released migration to represent a new schema change.
Add a new migration and test both upgrade and application startup behavior.

## Post-deployment verification

After the reverse proxy and DNS are configured, verify readiness:

```bash
curl --fail --silent --show-error \
  https://api.example.com/api/v1/utils/health/ready
```

Replace `api.example.com` with the deployed API hostname. A successful request
must return HTTP 200. Then use non-confidential data to verify administrator
sign-in, upload, indexing, retrieval, citations, metrics, and error reporting.

## Persistent data and backups

The deployment has three independent persistent data sets:

- `app-db-data`: application records, chunks, embeddings, and audit events
- `app-redis-data`: queued jobs and rate-limit state
- `app-upload-data`: uploaded source documents

Back up all three on a coordinated schedule. Store encrypted copies outside
the application host, restrict access, and test restoration regularly. A
backup that has never been restored is not a verified backup.

Never use `docker compose down --volumes` in production because it deletes the
named application volumes.

## Security requirements

- Terminate public traffic with HTTPS.
- Keep PostgreSQL and Redis off the public network.
- Disable Adminer when it is not needed. Do not expose it publicly without
  independent authentication and network access controls.
- Inject secrets through the platform or a restricted local secret file.
- Mount BGE-M3 read-only.
- Restrict access to uploaded documents and backups.
- Configure CORS only for the deployed frontend origin.
- Rotate credentials that appear in logs, commits, screenshots, or issues.
- Run `scripts/scan-secrets.ps1` before publishing a release candidate.

## Rollback

Use immutable image tags or digests so a previous application version can be
selected deliberately. Record current image identifiers and create a verified
database backup before deployment.

If an update fails:

1. Stop accepting new uploads.
2. Preserve backend, worker, and migration logs.
3. Determine whether the new migration is backward compatible.
4. Restore previous images when the schema remains compatible.
5. Restore the coordinated backup when schema rollback is required.
6. Re-run readiness and document-processing smoke tests.

Never downgrade containers across an incompatible schema without a reviewed
rollback migration or a verified backup restore.

## Release checklist

Before approving a deployment candidate:

- frontend lint and build pass
- backend Ruff, mypy, ty, and pytest checks pass
- Alembic reports a single migration head
- GitHub Actions configuration passes zizmor
- the secret scanner reports no leaks
- production secrets and model paths are outside Git
- database, Redis, and uploaded-file backups are verified
- deployment and rollback owners are identified
- health, upload, indexing, retrieval, and citation checks pass

Automatic production deployment is intentionally outside the current scope.
Add it only after the platform, credential model, approval gate, and rollback
procedure have been reviewed.
