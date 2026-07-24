"""CORS del walking skeleton — solo para dev local sin el proxy de nginx.

En compose (`docker/studio-nginx.conf`) `studio` y `api` son same-origin por
diseño (Task 2) — CORS no aplica ahí. Pero `api/README.md` documenta correr
`uv run uvicorn` suelto para dev, y el Studio en modo live (`vite`, origin
propio) le pega directo por red — ahí SÍ hace falta CORS explícito. Opt-in
por `CHIMERA_CORS_ORIGINS` (CSV) para no tocar el comportamiento same-origin-
only por defecto (prod/compose no setea la var).
"""

from __future__ import annotations

from typing import cast

import httpx
import pytest
from chimera_api.app import create_app
from fastapi.testclient import TestClient

from blite.events import create_event_store


def _options(
    client: TestClient, url: str, *, origin: str, method: str = "GET"
) -> httpx.Response:
    return cast(
        httpx.Response,
        client.options(  # pyright: ignore[reportUnknownMemberType]
            url,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": method,
            },
        ),
    )


class TestCorsDisabledByDefault:
    def test_sin_env_var_no_hay_cabeceras_cors(self) -> None:
        # Arrange — mismo comportamiento same-origin-only de siempre (compose)
        client = TestClient(create_app(create_event_store()))

        # Act
        response = _options(
            client, "/runs", origin="http://localhost:5173", method="POST"
        )

        # Assert
        assert "access-control-allow-origin" not in response.headers


class TestCorsHabilitadoPorEnv:
    def test_origen_configurado_recibe_cabecera_cors(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange
        monkeypatch.setenv("CHIMERA_CORS_ORIGINS", "http://localhost:5173")
        client = TestClient(create_app(create_event_store()))

        # Act
        response = _options(
            client, "/runs", origin="http://localhost:5173", method="POST"
        )

        # Assert
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:5173"
        )

    def test_origen_no_listado_no_recibe_cabecera_cors(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange
        monkeypatch.setenv("CHIMERA_CORS_ORIGINS", "http://localhost:5173")
        client = TestClient(create_app(create_event_store()))

        # Act — un origin que NO está en la lista
        response = _options(
            client, "/runs", origin="http://evil.example", method="POST"
        )

        # Assert
        assert "access-control-allow-origin" not in response.headers

    def test_csv_con_varios_origenes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        monkeypatch.setenv(
            "CHIMERA_CORS_ORIGINS", "http://localhost:5173,http://localhost:4173"
        )
        client = TestClient(create_app(create_event_store()))

        # Act
        response = _options(
            client, "/runs", origin="http://localhost:4173", method="POST"
        )

        # Assert
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:4173"
        )
