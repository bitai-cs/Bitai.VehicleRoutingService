# vehicle-routing-web

Plotly Dash app (Dash Bootstrap Components, Dash AG Grid) for uploading VRP payloads, solving them in batch against
`vehicle-routing-service`, and viewing results.

## Run

From the repository root:

```bash
uv run --directory apps/vehicle-routing-web vehicle-routing-web
uv run --directory apps/vehicle-routing-web pytest
uv run --directory apps/vehicle-routing-web ruff check .
uv run --directory apps/vehicle-routing-web ruff format --check .
```

Configuration is via `VRW_*` environment variables or `.env` (see `.env.example`). Relative paths such as
`VRW_STORAGE_DIR` resolve against the working directory. Run a single server process (threads are fine): the upload
de-duplication lock is process-local.

## Storage

```
<storage>/hashes.txt                              "<sha256-of-canonical-json> <process_id>" per line
<storage>/payloads/<id>/<id>-payload.json         payload as uploaded
<storage>/payloads/<id>/solver-result.json.pending  processing in progress
<storage>/payloads/<id>/solver-result.json        solver success
<storage>/payloads/<id>/solver-error.json         solver failure (user-safe: http_status, error_type, message, occurred_at)
```

File names are defined once in `domain/artifacts.py`. Status is derived only from which files exist: pending marker
=> running; result => solved; error => failed; none => pending. The marker always wins, so a stale result is never
shown as current. A marker left by a crashed server shows as running with a "run again" note and can be re-run.
