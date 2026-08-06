"""Smoke E2E del dominio runtime-api — plan `docs/mvp/01-runtime-api.md` §4.

"Smoke E2E: test de integración que hace POST /runs → espera terminal por
SSE → GET certificate → `check_bundle` 7/7. Ese test ES el MVP del dominio."
Ejercita el contrato completo del Studio/juez a través de la superficie HTTP
real — SOLO un test de integración, sin código de producción nuevo: reusa
el aparato ya construido por Task A/B/C (`tests/unit/api/test_runs.py`,
`tests/unit/api/test_certificate.py`,
`tests/unit/certificate/test_assemble.py`).

Bajo `TestClient` los `BackgroundTasks` de Starlette CORREN Y TERMINAN
dentro del ciclo de la request: tras `client.post("/runs")` el run ya
completó, así que un `GET .../events?live=0` (snapshot catch-up) devuelve el
stream completo INCLUYENDO el evento terminal — ese es el patrón de
"esperar terminal por SSE" en este harness (el tail infinito `live=True` no
se puede consumir bajo `TestClient`; ver `tests/unit/api/test_app_sse.py`).

NO se depende de capabilities instaladas y NO se mockea el motor: se
inyecta siempre una capability echo hermética vía `EntryPointRegistry`, pero
las dos patas de verificación (CP-SAT + pandapower) corren de verdad sobre
la red sintética de 4 buses — ese es exactamente el punto.
"""

from __future__ import annotations

import base64
import json
from typing import Any, cast

import httpx
from chimera_api.app import create_app
from fastapi.testclient import TestClient

from blite.certificate.bundle_check import check_bundle
from blite.events import create_event_store
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest

_STATEMENT_4BUS = "la partición propuesta es óptima y electricamente factible"
_SCOPE_4BUS: dict[str, Any] = {"instancia": "sintetica-4bus"}
_EDGES_4BUS = ((0, 1, 0), (2, 3, 0), (1, 2, 5))


class _EchoCapability:
    """Capability hermética de test — mismo patrón que
    `tests/unit/api/test_runs.py::_EchoCapability`."""

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.echo",
            description="generic test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"echoed": inputs["x"]}


def _make_client() -> TestClient:
    store = create_event_store()
    registry = EntryPointRegistry({"cap.echo": _EchoCapability()})
    return TestClient(create_app(store, registry=registry))


# starlette.testclient.TestClient anota `.get()`/`.post()` contra el paquete
# `httpx2` (bajo TYPE_CHECKING) que este repo no instala — el fallback en
# runtime es el `httpx` real, así que el cast es fiel al tipo efectivo en
# ejecución; pyright solo necesita el ignore puntual sobre la llamada (mismo
# patrón que `tests/unit/api/test_runs.py`/`test_certificate.py`).
def _get(client: TestClient, url: str) -> httpx.Response:
    return cast(
        httpx.Response,
        client.get(url),  # pyright: ignore[reportUnknownMemberType]
    )


def _post(client: TestClient, url: str, *, json_body: dict[str, Any]) -> httpx.Response:
    return cast(
        httpx.Response,
        client.post(url, json=json_body),  # pyright: ignore[reportUnknownMemberType]
    )


def _parse_frames(body: str) -> list[dict[str, str]]:
    frames: list[dict[str, str]] = []
    for chunk in body.split("\n\n"):
        if not chunk:
            continue
        frame: dict[str, str] = {}
        for line in chunk.split("\n"):
            key, _, value = line.partition(": ")
            frame[key] = value
        frames.append(frame)
    return frames


_CLOSING_EVENT_TYPES = frozenset({"run.metrics.recorded"})


def _hasta_el_terminal(frames: list[dict[str, str]]) -> list[dict[str, str]]:
    """[V2/M19] El cierre métrico se emite DESPUÉS del terminal (freeze §2
    [stress-final]: familia de cierre, fuera del hash). Preguntar cómo cerró
    el run es preguntar por el corte del provenance_hash, no por el último
    frame del stream."""
    return [f for f in frames if f["event"] not in _CLOSING_EVENT_TYPES]


def _predicate_of(bundle: dict[str, Any]) -> dict[str, Any]:
    """Mismo helper que `test_assemble.py`/`test_certificate.py`::_predicate_of
    — decodifica `envelope.payload` base64→json→["predicate"]."""
    payload = base64.b64decode(bundle["envelope"]["payload"])
    statement: dict[str, Any] = json.loads(payload)
    return statement["predicate"]


def _run_body(*, assignment: tuple[int, int, int, int]) -> dict[str, Any]:
    return {
        "capability_id": "cap.echo",
        "inputs": {"x": 21},
        "max_steps": 8,
        "claim": {
            "instance": {"n_nodes": 4, "edges": _EDGES_4BUS},
            "assignment": assignment,
            "canonical_statement": _STATEMENT_4BUS,
            "scope": _SCOPE_4BUS,
            "claim_type": "solution",
        },
    }


class TestGoldenPathE2E:
    """POST→SSE terminal→GET certificate→check_bundle 7/7 — el Nivel-1 del
    dominio."""

    def test_run_optimo_completa_7_de_7_con_titular_al3(self) -> None:
        # Arrange
        client = _make_client()

        # Act — POST /runs agenda el run.
        post_response = _post(
            client, "/runs", json_body=_run_body(assignment=(0, 0, 1, 1))
        )
        assert post_response.status_code == 202
        run_id = post_response.json()["run_id"]

        # Act — SSE: bajo TestClient los BackgroundTasks ya corrieron y
        # terminaron durante el POST, así que el snapshot `?live=0` observa
        # el stream completo hasta el evento terminal.
        events_response = _get(client, f"/runs/{run_id}/events?live=0")
        frames = _hasta_el_terminal(_parse_frames(events_response.text))
        types = [f["event"] for f in frames]
        assert frames[-1]["event"] == "run.completed"
        assert types.count("claim.emitted") == 1
        assert types.count("verification.completed") == 2

        # Act — GET certificate.
        cert_response = _get(client, f"/runs/{run_id}/certificate")
        assert cert_response.status_code == 200
        bundle = cert_response.json()

        # Assert — 7/7 offline, oráculo real.
        results = check_bundle(bundle)
        assert all(r.ok for r in results), [
            (r.number, r.failures) for r in results if not r.ok
        ]
        predicate = _predicate_of(bundle)
        assert predicate["titular_level"] == "AL3"
        assert {a["anchor_kind"] for a in predicate["attestations"]} == {
            "solver",
            "execution",
        }
        assert predicate["conclusions"][0]["verdict"] == "verified"


class TestRefutacionE2E:
    """El artefacto estrella: refutar es un veredicto de primera clase,
    verificable offline igual que un pass — mismo flujo POST→SSE→certificate."""

    def test_run_suboptimo_completa_7_de_7_con_titular_al0(self) -> None:
        # Arrange — assignment (0,0,0,1) aísla el bus 3 (sin slack): refuta
        # LIMPIO en las dos patas — formal (no es óptimo, corte 0 < 5) Y
        # execution (isla sin fuente, hard-fail antes de correr el flujo).
        # Mismo assignment que
        # `tests/unit/api/test_certificate.py::TestRefutacion` — ahí queda
        # documentado por qué (0,0,0,0) NO sirve: deja los dos slacks en la
        # misma isla conectada y la pata execution da "pass", dejando solo 1
        # pata en fail (el punto 7 exige 2 patas por independence_group).
        client = _make_client()

        # Act — POST /runs.
        post_response = _post(
            client, "/runs", json_body=_run_body(assignment=(0, 0, 0, 1))
        )
        assert post_response.status_code == 202
        run_id = post_response.json()["run_id"]

        # Act — SSE terminal.
        events_response = _get(client, f"/runs/{run_id}/events?live=0")
        frames = _hasta_el_terminal(_parse_frames(events_response.text))
        assert frames[-1]["event"] == "run.completed"

        # Act — GET certificate.
        cert_response = _get(client, f"/runs/{run_id}/certificate")
        assert cert_response.status_code == 200
        bundle = cert_response.json()

        # Assert — 7/7 offline, veredicto refutado, titular AL0.
        results = check_bundle(bundle)
        assert all(r.ok for r in results), [
            (r.number, r.failures) for r in results if not r.ok
        ]
        predicate = _predicate_of(bundle)
        assert predicate["conclusions"][0]["verdict"] == "refuted"
        assert predicate["titular_level"] == "AL0"
