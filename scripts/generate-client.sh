#! /usr/bin/env bash

set -e
set -x

cd backend
uv run python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > ../openapi.json
cd ..
mv openapi.json frontend/
bun run --filter techdoc-ai-frontend generate-client
bun -e 'for (const path of new Bun.Glob("frontend/src/client/**/*.ts").scanSync()) { const source = await Bun.file(path).text(); await Bun.write(path, source.replace(/[ \t]+(?=\r?$)/gm, "")); }'
bun run lint
