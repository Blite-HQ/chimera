"""Tests de los 6 GETs de lectura — spec `docs/specs/endpoints-studio.md`.

Cubre, por ruta: forma 200 (`RunSummary[]`/`ProjectArtifact[]`/
`KnowledgeClaim[]`/`StepDetail`/`AblationMetric[]`/payload de topología),
honest-empty (sin certificado/step/métricas/partición todavía → `[]` o
default vacío, jamás fabricado) y 404 fail-closed para un `run_id`/`step_id`
desconocido. Reusa el patrón hermético de `test_runs.py`/`test_certificate.py`
(capability echo + claim `sintetica-4bus` para el golden path real de dos
patas) para ejercer la rama CON certificado ya emitido, no solo la
honest-empty.
"""

from __future__ import annotations

from typing import Any, cast

import httpx
from chimera_api.app import create_app
from fastapi.testclient import TestClient

from blite.events import create_event_store
from blite.events.store import EventStore
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest

_STATEMENT_4BUS = "la partición propuesta es óptima y electricamente factible"
_SCOPE_4BUS: dict[str, Any] = {"instancia": "sintetica-4bus"}
_EDGES_4BUS = ((0, 1, 0), (2, 3, 0), (1, 2, 5))


class _EchoCapability:
    """Capability hermética de test — mismo patrón que `test_runs.py`."""

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


def _make_registry() -> EntryPointRegistry:
    return EntryPointRegistry({"cap.echo": _EchoCapability()})


def _make_client(store: EventStore | None = None) -> TestClient:
    event_store = store if store is not None else create_event_store()
    return TestClient(create_app(event_store, registry=_make_registry()))


# Mismo patrón de pyright-ignore puntual que `test_runs.py`/`test_certificate.py`.
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


def _run_body() -> dict[str, Any]:
    return {
        "capability_id": "cap.echo",
        "inputs": {"x": 21},
        "claim": {
            "instance": {"n_nodes": 4, "edges": _EDGES_4BUS},
            "assignment": (0, 0, 1, 1),
            "canonical_statement": _STATEMENT_4BUS,
            "scope": _SCOPE_4BUS,
            "claim_type": "solution",
        },
    }


def _create_golden_run(client: TestClient) -> str:
    """Run real de dos patas (formal + eléctrica), terminado con certificado
    asamblable — bajo `TestClient` los `BackgroundTasks` ya corrieron."""
    response = _post(client, "/runs", json_body=_run_body())
    assert response.status_code == 202
    run_id: str = response.json()["run_id"]
    return run_id


def _seed_bare_run(
    store: EventStore, run_id: str, *, terminal_type: str = "run.completed"
) -> None:
    """Un run mínimo terminado SIN ticket (nunca pasó por `POST /runs`) —
    conocido por la proyección, pero sin certificado asamblable: la rama
    honest-empty de `GET /runs`, `.../artifacts` y `.../knowledge`.

    `terminal_type` (auditoría Fase 2, `docs/mvp/decisiones.md`
    §"Análisis para discusión" punto 3, extensión aditiva): además de
    `run.completed`, acepta `run.failed`/`run.cancelled` — los tres son
    `TERMINAL_RUN_EVENTS` (freeze §2) y `_run_status` debe distinguirlos."""
    store.append(
        stream_id=run_id,
        type="run.created",
        actor_id="user:dylan",
        domain_id="d-default",
        payload={"run_id": run_id, "max_steps": 8, "policy_digest": "sha256:pp"},
    )
    store.append(
        stream_id=run_id,
        type=terminal_type,
        actor_id="service:runtime",
        domain_id="d-default",
        payload={},
        expected_seq=1,
    )


class TestGetRuns:
    def test_run_sin_certificado_lista_con_campos_honestos_en_null(self) -> None:
        # Arrange
        store = create_event_store()
        _seed_bare_run(store, "r1")
        client = _make_client(store)

        # Act
        response = _get(client, "/runs")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        row = body[0]
        assert row["run_id"] == "r1"
        assert row["status"] == "completado"
        assert row["conclusion"] is None
        assert row["verdict"] is None
        assert row["titular_level"] is None
        assert row["titular_class"] is None
        assert row["events_count"] == 2
        assert row["actor"] == "user:dylan"

    def test_run_con_certificado_real_trae_conclusion_y_verdict(self) -> None:
        # Arrange
        client = _make_client()
        run_id = _create_golden_run(client)

        # Act
        response = _get(client, "/runs")

        # Assert
        assert response.status_code == 200
        row = next(r for r in response.json() if r["run_id"] == run_id)
        assert row["status"] == "completado"
        assert row["conclusion"] == _STATEMENT_4BUS
        assert row["verdict"] == "verified"
        assert row["titular_level"] == "AL3"
        assert row["titular_class"] == "formal_exact"
        assert row["completed_at"] is not None

    def test_store_vacio_da_lista_vacia(self) -> None:
        client = _make_client()
        response = _get(client, "/runs")
        assert response.status_code == 200
        assert response.json() == []

    def test_run_terminado_en_failed_lista_fallido_no_en_curso_para_siempre(
        self,
    ) -> None:
        """Auditoría Fase 2 (verificado vivo, `docs/mvp/decisiones.md`
        §"Análisis para discusión" punto 3): antes de esta extensión aditiva,
        un run que cerró con `run.failed` quedaba "en_curso" PARA SIEMPRE en
        `GET /runs` (el enum wire no tenía `fallido`)."""
        # Arrange
        store = create_event_store()
        _seed_bare_run(store, "r1", terminal_type="run.failed")
        client = _make_client(store)

        # Act
        response = _get(client, "/runs")

        # Assert
        assert response.status_code == 200
        row = response.json()[0]
        assert row["status"] == "fallido"

    def test_run_terminado_en_cancelled_lista_cancelado(self) -> None:
        # Arrange
        store = create_event_store()
        _seed_bare_run(store, "r1", terminal_type="run.cancelled")
        client = _make_client(store)

        # Act
        response = _get(client, "/runs")

        # Assert
        assert response.status_code == 200
        row = response.json()[0]
        assert row["status"] == "cancelado"


class TestDeliverablesDelCertificado:
    """[V8/M23b · N4/#70b] `assemble_bundle` aceptaba `deliverables=` desde
    siempre y NADIE se lo pasaba: `GET /runs/{id}/artifacts` devolvía `[]`
    para todo run — honest-empty ESTRUCTURAL, no falta de datos."""

    def test_un_run_completado_cita_su_artefacto_de_salida(self) -> None:
        # Arrange / Act
        client = _make_client()
        run_id = _create_golden_run(client)

        # Assert
        body = _get(client, f"/runs/{run_id}/artifacts").json()
        assert [a["artifact_ref"] for a in body] == [f"runs/{run_id}/output.json"]
        assert body[0]["run_id"] == run_id
        assert body[0]["titular_level"] == "AL3"
        assert body[0]["verdict"] == "verified"

    def test_el_digest_citado_es_el_output_digest_del_log(self) -> None:
        """La cita es verificable: el certificado y el log nombran los MISMOS
        bytes. Si divergieran, el enlace del certificado sería decorativo."""
        # Arrange
        store = create_event_store()
        client = _make_client(store)

        # Act
        run_id = _create_golden_run(client)
        artefactos = _get(client, f"/runs/{run_id}/artifacts").json()
        completado = next(
            e for e in store.read_stream(run_id) if e.type == "run.completed"
        )

        # Assert
        assert artefactos[0]["digest"] == completado.payload["output_digest"]

    def test_un_run_sin_salida_recuperable_no_cita_nada_roto(self) -> None:
        """Fail-closed sin ruido: el certificado se emite con la lista vacía
        antes que con un enlace que nadie puede resolver."""
        store = create_event_store()
        _seed_bare_run(store, "r1")
        client = _make_client(store)

        assert _get(client, "/runs/r1/artifacts").json() == []


class TestRutasDeProyecto:
    """[V8/M23b · N4] Artifacts/Knowledge de NIVEL PROYECTO: la superficie que
    la doctrina prometía («conclusiones verificadas acumuladas») y que no
    existía — el Studio devolvía `[]` en vivo por no tener a quién preguntar."""

    def test_agrega_los_deliverables_de_todos_los_runs(self) -> None:
        # Arrange
        client = _make_client()
        primero = _create_golden_run(client)
        segundo = _create_golden_run(client)

        # Act
        body = _get(client, "/artifacts").json()

        # Assert
        assert sorted(a["run_id"] for a in body) == sorted([primero, segundo])

    def test_agrega_el_conocimiento_verificado_de_todos_los_runs(self) -> None:
        # Arrange
        client = _make_client()
        _create_golden_run(client)
        _create_golden_run(client)

        # Act
        body = _get(client, "/knowledge").json()

        # Assert
        assert len(body) == 2
        assert {k["statement"] for k in body} == {_STATEMENT_4BUS}

    def test_un_proyecto_sin_runs_da_listas_vacias_honestas(self) -> None:
        client = _make_client()
        assert _get(client, "/artifacts").json() == []
        assert _get(client, "/knowledge").json() == []

    def test_un_run_sin_certificado_no_aporta_ni_rompe_el_agregado(self) -> None:
        """Skip honesto (#104) aplicado al agregado: un run sin bundle no
        aparece, y no impide que los demás sí."""
        # Arrange
        store = create_event_store()
        _seed_bare_run(store, "r-sin-cert")
        client = _make_client(store)
        con_cert = _create_golden_run(client)

        # Act
        body = _get(client, "/artifacts").json()

        # Assert
        assert [a["run_id"] for a in body] == [con_cert]


class TestGetRunArtifacts:
    def test_run_sin_certificado_da_lista_vacia_honesta(self) -> None:
        store = create_event_store()
        _seed_bare_run(store, "r1")
        client = _make_client(store)

        response = _get(client, "/runs/r1/artifacts")

        assert response.status_code == 200
        assert response.json() == []

    def test_run_desconocido_da_404(self) -> None:
        client = _make_client()
        response = _get(client, "/runs/no-existe/artifacts")
        assert response.status_code == 404


class TestGetRunKnowledge:
    def test_run_con_certificado_expone_la_conclusion_verificada(self) -> None:
        client = _make_client()
        run_id = _create_golden_run(client)

        response = _get(client, f"/runs/{run_id}/knowledge")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        claim = body[0]
        assert claim["statement"] == _STATEMENT_4BUS
        assert claim["verdict"] == "verified"
        assert claim["level"] == "AL3"
        assert claim["titular_class"] == "formal_exact"
        assert claim["run_id"] == run_id

    def test_run_sin_certificado_da_lista_vacia_honesta(self) -> None:
        store = create_event_store()
        _seed_bare_run(store, "r1")
        client = _make_client(store)

        response = _get(client, "/runs/r1/knowledge")

        assert response.status_code == 200
        assert response.json() == []

    def test_run_desconocido_da_404(self) -> None:
        client = _make_client()
        response = _get(client, "/runs/no-existe/knowledge")
        assert response.status_code == 404


class TestGetStepEvidence:
    def test_step_con_capability_job_trae_los_digests(self) -> None:
        # El paso "invoke" (step-2, freeze §3 step<->job 1:1) lleva
        # `capability_id`/`input_digest`/`output_digest` — los emite
        # `capability.job.*`, que SÍ carga `step_id` (loop.py).
        #
        # [V1/M18 — M23a/N3] Las `attestations` YA NO llegan vacías: el
        # orquestador hilvana el `step_id` que el loop siempre le pasó, así
        # que la ruta puede atribuir al paso las dos patas del golden path.
        # El hallazgo previo ("honesto, no fabricado; hallazgo para el
        # reporte") queda cerrado acá.
        client = _make_client()
        run_id = _create_golden_run(client)

        response = _get(client, f"/runs/{run_id}/steps/step-2/evidence")

        assert response.status_code == 200
        body = response.json()
        assert body["step_id"] == "step-2"
        assert body["capability_id"] == "cap.echo"
        assert body["input_digest"] is not None
        assert body["output_digest"] is not None
        assert [a["verifier_id"] for a in body["attestations"]] == [
            "verifier:cpsat-differential",
            "verifier:pandapower-islanding",
        ]

    def test_step_conocido_sin_verificacion_da_attestations_vacio(self) -> None:
        store = create_event_store()
        run_id = "r1"
        store.append(
            stream_id=run_id,
            type="run.created",
            actor_id="user:dylan",
            domain_id="d-default",
            payload={"run_id": run_id, "max_steps": 8, "policy_digest": "sha256:pp"},
        )
        store.append(
            stream_id=run_id,
            type="run.step.started",
            actor_id="service:runtime",
            domain_id="d-default",
            payload={
                "step_id": "s1",
                "run_id": run_id,
                "kind": "invoke",
                "input_digest": "sha256:in",
                "status": "running",
            },
            expected_seq=1,
        )
        client = _make_client(store)

        response = _get(client, f"/runs/{run_id}/steps/s1/evidence")

        assert response.status_code == 200
        body = response.json()
        assert body["step_id"] == "s1"
        assert body["attestations"] == []

    def test_step_desconocido_da_404(self) -> None:
        store = create_event_store()
        run_id = "r1"
        store.append(
            stream_id=run_id,
            type="run.created",
            actor_id="user:dylan",
            domain_id="d-default",
            payload={"run_id": run_id, "max_steps": 8, "policy_digest": "sha256:pp"},
        )
        client = _make_client(store)

        response = _get(client, f"/runs/{run_id}/steps/no-existe/evidence")

        assert response.status_code == 404

    def test_run_desconocido_da_404(self) -> None:
        client = _make_client()
        response = _get(client, "/runs/no-existe/steps/s1/evidence")
        assert response.status_code == 404


class TestGetAblation:
    def test_sin_metricas_registradas_da_lista_vacia_honesta(self) -> None:
        store = create_event_store()
        _seed_bare_run(store, "r1")
        client = _make_client(store)

        response = _get(client, "/runs/r1/ablation")

        assert response.status_code == 200
        assert response.json() == []

    def test_metricas_registradas_por_variante_se_exponen_tal_cual(self) -> None:
        store = create_event_store()
        run_id = "r1"
        store.append(
            stream_id=run_id,
            type="run.created",
            actor_id="user:dylan",
            domain_id="d-default",
            payload={"run_id": run_id, "max_steps": 8, "policy_digest": "sha256:pp"},
        )
        store.append(
            stream_id=run_id,
            type="run.metrics.recorded",
            actor_id="service:runtime",
            domain_id="d-default",
            payload={
                "variant": "quantum",
                "cut_cost": 5.0,
                "wall_ms": 120.5,
                "verification_latency_ms": 30.0,
            },
            expected_seq=1,
        )
        client = _make_client(store)

        response = _get(client, f"/runs/{run_id}/ablation")

        assert response.status_code == 200
        body = response.json()
        assert body == [
            {
                "variant": "quantum",
                "cut_cost": 5.0,
                "wall_ms": 120.5,
                "verification_latency_ms": 30.0,
            }
        ]

    def test_run_desconocido_da_404(self) -> None:
        client = _make_client()
        response = _get(client, "/runs/no-existe/ablation")
        assert response.status_code == 404

    def test_las_cuatro_variantes_del_enum_pasan_la_ruta(self) -> None:
        """[V2/M19 · C-4] El enum creció de 2 a 4 EN EL MISMO checkpoint que
        su productor — `mitigated`/`zne` (M6) ya no rebotan en la frontera."""
        store = create_event_store()
        for indice, variante in enumerate(("quantum", "classical", "mitigated", "zne")):
            run_id = f"r-{variante}"
            store.append(
                stream_id=run_id,
                type="run.created",
                actor_id="user:dylan",
                domain_id="d-default",
                payload={
                    "run_id": run_id,
                    "max_steps": 8,
                    "policy_digest": "sha256:pp",
                },
            )
            store.append(
                stream_id=run_id,
                type="run.metrics.recorded",
                actor_id="service:runtime",
                domain_id="d-default",
                payload={
                    "variant": variante,
                    "cut_cost": float(indice),
                    "wall_ms": 1.0,
                    "verification_latency_ms": 1.0,
                },
                expected_seq=1,
            )
        client = _make_client(store)

        for variante in ("quantum", "classical", "mitigated", "zne"):
            body = _get(client, f"/runs/r-{variante}/ablation").json()
            assert [fila["variant"] for fila in body] == [variante]

    def test_un_cierre_solo_de_confianza_no_aparece_como_punto_cientifico(
        self,
    ) -> None:
        """[V2/M19] TODO run terminado emite `run.metrics.recorded`, pero uno
        sin `variant`/`cut_cost`/`wall_ms` no es una fila de ablación — se
        omite en vez de inventarle una variante."""
        # Arrange / Act
        client = _make_client()
        run_id = _create_golden_run(client)

        # Assert
        assert _get(client, f"/runs/{run_id}/ablation").json() == []


class TestAblacionAgregaLosBrazos:
    """[V2/M19 · C-4] Los dos brazos son SUB-RUNS (§13): cada uno emite SU
    cierre en SU stream. Preguntarle solo al raíz devolvería un panel de una
    barra para una comparación de dos."""

    @staticmethod
    def _con_dos_brazos(store: EventStore) -> None:
        from blite.runtime.ablation import AblationArm, run_ablation_arms
        from blite.runtime.content_store import InMemoryContentStore
        from blite.runtime.dispatch import ProfileDispatcher

        store.append(
            stream_id="raiz",
            type="run.created",
            actor_id="user:dylan",
            domain_id="d-default",
            payload={
                "run_id": "raiz",
                "actor_id": "user:dylan",
                "domain_id": "d-default",
                "max_steps": 4,
                "policy_digest": "p" * 64,
            },
        )
        run_ablation_arms(
            store,
            _make_registry(),
            ProfileDispatcher(),
            InMemoryContentStore(),
            root_run_id="raiz",
            root_policy_digest="p" * 64,
            actor_id="user:dylan",
            domain_id="d-default",
            arms=[
                AblationArm(
                    variant="quantum",
                    capability_id="cap.echo",
                    inputs={"x": 1},
                    cut_cost=5.0,
                ),
                AblationArm(
                    variant="classical",
                    capability_id="cap.echo",
                    inputs={"x": 2},
                    cut_cost=7.0,
                ),
            ],
        )

    def test_el_panel_del_raiz_muestra_las_dos_barras(self) -> None:
        # Arrange
        store = create_event_store()
        self._con_dos_brazos(store)
        client = _make_client(store)

        # Act
        body = _get(client, "/runs/raiz/ablation").json()

        # Assert — orden determinista y en el orden DECLARADO de los brazos:
        # el id del sub-run lleva el índice, así que ordenar por id preserva
        # el orden del experimento (dos renders dan el mismo panel).
        assert [fila["variant"] for fila in body] == ["quantum", "classical"]
        assert [fila["cut_cost"] for fila in body] == [5.0, 7.0]

    def test_cada_brazo_conserva_su_propio_panel(self) -> None:
        """Agregación de LECTURA: nada se fusiona — cada brazo sigue teniendo
        su stream, su procedencia y su propia respuesta."""
        # Arrange
        store = create_event_store()
        self._con_dos_brazos(store)
        client = _make_client(store)

        # Act
        propio = _get(client, "/runs/raiz--arm-0-quantum/ablation").json()

        # Assert
        assert [fila["variant"] for fila in propio] == ["quantum"]


class TestGetTopology:
    def test_sin_particion_embebida_da_payload_vacio_honesto(self) -> None:
        store = create_event_store()
        _seed_bare_run(store, "r1")
        client = _make_client(store)

        response = _get(client, "/runs/r1/topology")

        assert response.status_code == 200
        body = response.json()
        for key in ("topology_ref", "islands", "cut_branch_ids", "cut_cost"):
            assert key in body
        assert body["islands"] == []

    def test_run_desconocido_da_404(self) -> None:
        client = _make_client()
        response = _get(client, "/runs/no-existe/topology")
        assert response.status_code == 404

    def test_el_golden_path_produce_la_particion_real(self) -> None:
        """V1/M18: el productor que faltaba. Un run REAL de dos patas emite la
        partición embebida en `verification.completed` y la ruta la proyecta —
        los badges del mapa salen de la pata de ejecución que corrió de
        verdad, no de un fixture."""
        # Arrange
        client = _make_client()

        # Act
        run_id = _create_golden_run(client)
        body = _get(client, f"/runs/{run_id}/topology").json()

        # Assert — dos islas verificadas, cada una con SU bloque (freeze §9)
        assert body["topology_ref"] == "sintetica-4bus"
        assert [isla["id"] for isla in body["islands"]] == ["island-0", "island-1"]
        for isla in body["islands"]:
            assert isla["verification"]["verdict"] == "pass"
            assert isla["verification"]["verifier_class"] == "execution"
            assert isla["verification"]["level"] == "AL3"
        assert [isla["bus_ids"] for isla in body["islands"]] == [["0", "1"], ["2", "3"]]

    def test_el_corte_cita_la_convencion_de_branch_ids(self) -> None:
        """C-8: `cut_branch_ids` con identidad estable — la arista (1,2) es la
        única que cruza en la partición del golden path."""
        # Arrange
        client = _make_client()

        # Act
        run_id = _create_golden_run(client)
        body = _get(client, f"/runs/{run_id}/topology").json()

        # Assert
        assert body["cut_branch_ids"] == ["L1-2"]
        assert body["cut_cost"] == 5.0
