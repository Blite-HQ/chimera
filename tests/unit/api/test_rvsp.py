"""`GET /runs/{run_id}/rvsp` — la curva r-vs-p por run (V3/M20 · C-9/#125).

Contrato: `docs/specs/endpoints-studio.md` §"GET /runs/{run_id}/rvsp". Clave
POR RUN: el run cita su instancia y la ruta sirve la curva CONGELADA de esa
instancia (`knowledge/rvsp/<instancia>.json`, producida por
`scripts/gen_corpus_rvsp.py`).

Los tres 404 honestos que se prueban acá son el corazón de la ruta: run
desconocido, run que no declara instancia, e instancia sin curva ingerida.
Ninguno de los tres puede degradar a "una curva vacía" o a puntos
fabricados — un gráfico con datos inventados es exactamente el mock
silencioso que este proyecto prohíbe.
"""

from __future__ import annotations

from typing import Any, cast

import httpx
import pytest
from chimera_api.app import create_app
from fastapi.testclient import TestClient

from blite.events import create_event_store
from blite.events.store import EventStore
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest
from tests.conftest import authenticated

_EDGES_4BUS = ((0, 1, 0), (2, 3, 0), (1, 2, 5))
_STATEMENT = "la partición propuesta es óptima y electricamente factible"
_INSTANCIA_CON_CURVA = "cr8-uniforme"
_INSTANCIA_SIN_CURVA = "sintetica-4bus"


class _EchoCapability:
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


def _make_client(store: EventStore | None = None) -> TestClient:
    return authenticated(
        TestClient(
            create_app(
                store if store is not None else create_event_store(),
                registry=EntryPointRegistry({"cap.echo": _EchoCapability()}),
            )
        )
    )


def _get(client: TestClient, url: str) -> httpx.Response:
    return cast(
        httpx.Response,
        client.get(url),
    )


def _post(client: TestClient, url: str, *, json_body: dict[str, Any]) -> httpx.Response:
    return cast(
        httpx.Response,
        client.post(url, json=json_body),
    )


def _crear_run(client: TestClient, instancia: str) -> str:
    """Run claim-first real (mismo patrón hermético que `test_reads.py`) —
    lo único que importa acá es la instancia que el claim declara."""
    respuesta = _post(
        client,
        "/runs",
        json_body={
            "capability_id": "cap.echo",
            "inputs": {"x": 21},
            "claim": {
                "instance": {"n_nodes": 4, "edges": _EDGES_4BUS},
                "assignment": (0, 0, 1, 1),
                "canonical_statement": _STATEMENT,
                "scope": {"instancia": instancia},
                "claim_type": "solution",
            },
        },
    )
    assert respuesta.status_code == 202, respuesta.text
    return str(respuesta.json()["run_id"])


class TestCuatroCientoCuatroHonestos:
    def test_run_desconocido(self) -> None:
        respuesta = _get(_make_client(), "/runs/inexistente/rvsp")

        assert respuesta.status_code == 404
        assert respuesta.json()["detail"] == "run desconocido"

    def test_run_que_no_declara_instancia(self) -> None:
        """Un run que este proceso no arrancó (o que no cita instancia) no
        tiene de dónde sacar QUÉ curva servir — y adivinar una sería servir
        la ciencia de otra red."""
        # Arrange
        store = create_event_store()
        store.append(
            stream_id="run-sin-instancia",
            type="run.created",
            actor_id="user:dylan",
            domain_id="domain-default",
            payload={
                "run_id": "run-sin-instancia",
                "actor_id": "user:dylan",
                "domain_id": "domain-default",
                "max_steps": 4,
                "policy_digest": "d" * 64,
            },
            expected_seq=0,
        )

        # Act
        respuesta = _get(_make_client(store), "/runs/run-sin-instancia/rvsp")

        # Assert
        assert respuesta.status_code == 404
        assert "rvsp" in respuesta.json()["detail"].lower()

    def test_instancia_sin_curva_ingerida(self) -> None:
        """`sintetica-4bus` no tiene barrido congelado — la ruta jamás
        inventa puntos (letra C-9: el productor es V3, no la ruta)."""
        # Arrange
        client = _make_client()
        run_id = _crear_run(client, _INSTANCIA_SIN_CURVA)

        # Act
        respuesta = _get(client, f"/runs/{run_id}/rvsp")

        # Assert
        assert respuesta.status_code == 404
        assert "rvsp" in respuesta.json()["detail"].lower()


class TestCurvaServida:
    @pytest.fixture
    def curva(self) -> dict[str, Any]:
        client = _make_client()
        run_id = _crear_run(client, _INSTANCIA_CON_CURVA)
        respuesta = _get(client, f"/runs/{run_id}/rvsp")
        assert respuesta.status_code == 200, respuesta.text
        return cast("dict[str, Any]", respuesta.json())

    def test_el_wire_tiene_exactamente_la_forma_congelada(
        self, curva: dict[str, Any]
    ) -> None:
        """snake_case y las 4 claves del contrato, sin el bloque `metodo`
        del record: el wire es lo que la spec congeló, no el artefacto entero."""
        # Assert
        assert set(curva) == {"instance", "optimo", "baselines", "points"}
        assert curva["instance"] == _INSTANCIA_CON_CURVA
        assert curva["optimo"] > 0
        assert set(curva["points"][0]) == {
            "p",
            "r_esperado_mean",
            "r_muestral_mean",
            "r_muestral_std",
            "r_muestral_min",
            "r_muestral_max",
            "success_rate",
        }

    def test_las_baselines_son_las_tres_del_contrato(
        self, curva: dict[str, Any]
    ) -> None:
        """Cerrado a 3 (C-15): se extiende COORDINADO cuando llegue `sa`,
        jamás con un catchall que dejaría entrar una serie que ningún chart
        sabe pintar."""
        # Assert
        assert set(curva["baselines"]) == {"cpsat", "greedy", "gw"}
        assert curva["baselines"]["cpsat"]["r"] == 1.0

    def test_toda_razon_vive_entre_cero_y_uno(self, curva: dict[str, Any]) -> None:
        """El `rvspSchema` del Studio lo exige; que el server pueda emitir
        algo que su propio espejo rechaza sería la costura rota."""
        # Assert
        for punto in curva["points"]:
            assert 0.0 <= punto["r_esperado_mean"] <= 1.0
            assert 0.0 <= punto["r_muestral_mean"] <= 1.0
            assert punto["r_muestral_std"] >= 0.0

    def test_los_puntos_suben_por_capa_sin_repetirse(
        self, curva: dict[str, Any]
    ) -> None:
        """Orden determinista y una fila por p — el eje x del gráfico no se
        arma con un `sort` del cliente."""
        # Assert
        ps = [punto["p"] for punto in curva["points"]]
        assert ps == sorted(ps)
        assert len(ps) == len(set(ps))


class TestCorpusCongelado:
    def test_un_record_tamperado_no_se_sirve(self, tmp_path: Any) -> None:
        """MISMA disciplina de identidad que el resto de `knowledge/`: si el
        digest embebido no cierra sobre el contenido, el record no existe
        para la ruta — fail-closed, jamás un 500 ni un dato no verificado."""
        # Arrange
        import json

        from chimera_api.rvsp import load_rvsp_record

        sano: dict[str, Any] = {
            "instance": "x",
            "optimo": 5,
            "baselines": {
                "cpsat": {"energy": 5.0, "r": 1.0},
                "greedy": {"energy": 4.0, "r": 0.8},
                "gw": {"energy": 4.0, "r": 0.8},
            },
            "points": [],
            "digest": "0" * 64,
        }
        (tmp_path / "x.json").write_text(json.dumps(sano), encoding="utf-8")

        # Act / Assert
        assert load_rvsp_record("x", directory=tmp_path) is None

    def test_un_slug_de_traversal_no_toca_el_filesystem(self) -> None:
        """El `instance_id` viaja desde un body HTTP: jamás se interpola en
        una ruta sin pasar por el guard de slug primero."""
        from chimera_api.rvsp import load_rvsp_record

        assert load_rvsp_record("../../etc/passwd") is None
