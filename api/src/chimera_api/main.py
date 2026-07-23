"""Entrypoint de uvicorn: `uv run uvicorn chimera_api.main:app`."""

from chimera_api.app import create_app

app = create_app()
