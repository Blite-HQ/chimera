"""Seed del skip honesto de lectura (#104/#123 — S-B, píldora #96 como caso).

Contrato: docs/specs/endpoints-studio.md §"GET /runs/discarded". La ruta de
LECTURA descarta streams envenenados sin tumbar el listado; la ruta hermana
los reporta. Escritura/certificados/provenance siguen fail-loud (línea roja
de #104) — este seed NO toca ese camino. Implementación = ítem P2 (Fase 1).
"""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason=(
            "Fase 1 P2: el skip por-stream y GET /runs/discarded no existen — "
            "docs/specs/endpoints-studio.md §GET /runs/discarded (#104/#123)"
        ),
    ),
]


def _store_con_pildora() -> Any:
    """Un run sano + la píldora #96: run.created SIN policy_digest/max_steps."""
    from blite.events import create_event_store

    store = create_event_store()
    store.append(
        stream_id="run-sano",
        type="run.created",
        actor_id="user:dylan",
        domain_id="domain-default",
        payload={
            "run_id": "run-sano",
            "actor_id": "user:dylan",
            "domain_id": "domain-default",
            "max_steps": 4,
            "policy_digest": "d" * 64,
        },
        expected_seq=0,
    )
    store.append(
        stream_id="run-envenenado",
        type="run.created",
        actor_id="user:dylan",
        domain_id="domain-default",
        payload={"run_id": "run-envenenado"},
        expected_seq=0,
    )
    return store


def _client(store: Any) -> Any:
    from chimera_api.app import create_app
    from fastapi.testclient import TestClient

    return TestClient(create_app(store))


def test_get_runs_omite_el_stream_envenenado() -> None:
    """La píldora ya no tumba el listado: 200 con SOLO los streams sanos."""
    client = _client(_store_con_pildora())
    respuesta = client.get("/runs")
    assert respuesta.status_code == 200
    run_ids = [fila["run_id"] for fila in respuesta.json()]
    assert run_ids == ["run-sano"]


def test_get_runs_discarded_reporta_el_descartado() -> None:
    """La ruta hermana expone {stream_id, error_kind} del stream omitido."""
    client = _client(_store_con_pildora())
    respuesta = client.get("/runs/discarded")
    assert respuesta.status_code == 200
    descartados = respuesta.json()["discarded_streams"]
    assert [fila["stream_id"] for fila in descartados] == ["run-envenenado"]
    assert descartados[0]["error_kind"]


def test_get_runs_discarded_vacio_honesto() -> None:
    """Sin píldora, el reporte es vacío honesto — jamás filas fabricadas."""
    from blite.events import create_event_store

    client = _client(create_event_store())
    respuesta = client.get("/runs/discarded")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"discarded_streams": []}
