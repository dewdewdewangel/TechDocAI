# Contributing to TechDoc AI

Thank you for contributing to TechDoc AI.

## Before starting

For architectural changes, new dependencies, document-processing changes,
retrieval changes, or security-sensitive work, open an issue or discussion
before implementation.

Small bug fixes, tests, and documentation improvements may go directly to a
pull request.

## Development requirements

- Do not commit `.env`, `.env.local`, uploaded documents, model weights, or
  authentication state.
- Run `./scripts/scan-secrets.ps1` before submitting changes.
- Add or update tests for behavior changes.
- Preserve third-party attribution and generated-file markers.
- Do not manually edit generated OpenAPI client or route-tree files.

## Required checks

Backend:

```powershell
cd backend
uv run ruff check app tests scripts
uv run ty check app
uv run mypy app
uv run pytest

```

Frontend commands, run from the repository root:

```powershell
bun install --frozen-lockfile
bun run --filter techdoc-ai-frontend build
```