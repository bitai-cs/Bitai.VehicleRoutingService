# Bitai Vehicle Routing Solution

uv workspace containing the apps that make up this solution.

## Apps

- [`apps/vehicle-routing-service`](apps/vehicle-routing-service) — FastAPI RESTful web API exposing the vehicle
  routing (VRP) solver.
- `apps/vehicle-routing-web` — Django web app that consumes `vehicle-routing-service`.

## Workspace

This repository is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/): a single root
`pyproject.toml` and a single `uv.lock`/`.venv` shared across all apps under `apps/`. The root project itself is
virtual (`[tool.uv] package = false`) — it is not installed, it only declares the workspace.

Common commands, run from the repository root:

```bash
# Install/sync all workspace members into the shared .venv
uv sync

# Run a command inside a specific app (its own pyproject.toml, dependencies, config files)
uv run --directory apps/vehicle-routing-service vehicle-routing-service
uv run --directory apps/vehicle-routing-service pytest -q
```

Each app keeps its own `pyproject.toml`, source layout, and (where applicable) `.env` file, so always run app
commands with `--directory apps/<app-name>` (or `cd` into it first) — relative paths like `.env` are resolved
against the current working directory.
