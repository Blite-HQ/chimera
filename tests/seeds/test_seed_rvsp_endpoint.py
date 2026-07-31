"""Seed del endpoint GET /runs/{run_id}/rvsp (C-9/#106 · #125 — S-D).

Contrato: docs/specs/endpoints-studio.md §"GET /runs/{run_id}/rvsp". Clave
POR RUN; 404 honesto para run desconocido Y para run sin datos rvsp (el
productor — ángulos de Nexus ingeridos con digest — es V3/M20; la ruta jamás
inventa puntos). Implementación = ítem V3/M20 (Fase 1).
"""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason=(
            "Fase 1 V3/M20: GET /runs/{run_id}/rvsp no existe todavía — "
            "docs/specs/endpoints-studio.md (C-9/#125)"
        ),
    ),
]


def _client(store: Any) -> Any:
    from chimera_api.app import create_app
    from fastapi.testclient import TestClient

    return TestClient(create_app(store))


def test_rvsp_404_para_run_desconocido() -> None:
    """Mismo patrón fail-closed que el resto de rutas de lectura."""
    from blite.events import create_event_store

    respuesta = _client(create_event_store()).get("/runs/inexistente/rvsp")
    assert respuesta.status_code == 404
    # el detail del app distingue la ruta implementada del 404 de FastAPI por
    # ruta inexistente — sin esto el seed pasaría vacuo antes de Fase 1
    assert respuesta.json()["detail"] == "run desconocido"


def test_rvsp_404_honesto_sin_productor() -> None:
    """Un run real SIN datos rvsp ingeridos: 404 con detail — jamás una
    curva fabricada (letra C-9: ice-* con optimo null quedan FUERA)."""
    from blite.events import create_event_store

    store = create_event_store()
    store.append(
        stream_id="run-sin-rvsp",
        type="run.created",
        actor_id="user:dylan",
        domain_id="domain-default",
        payload={
            "run_id": "run-sin-rvsp",
            "actor_id": "user:dylan",
            "domain_id": "domain-default",
            "max_steps": 4,
            "policy_digest": "d" * 64,
        },
        expected_seq=0,
    )
    respuesta = _client(store).get("/runs/run-sin-rvsp/rvsp")
    assert respuesta.status_code == 404
    assert "rvsp" in respuesta.json()["detail"].lower()
