"""Brazos de ablación como sub-runs (V2/M19 · C-4, freeze §13).

Lo que se prueba: cada brazo tiene SU stream, SU cierre métrico con SU
variante, y aporta sus claims al raíz con el hash de procedencia — que es lo
que hace que el certificado del raíz ampare transitivamente los dos brazos en
vez de que sean dos corridas sin relación declarada.
"""

from __future__ import annotations

from typing import Any

from blite.events import create_event_store
from blite.runtime.ablation import AblationArm, run_ablation_arms
from blite.runtime.content_store import InMemoryContentStore
from blite.runtime.dispatch import ProfileDispatcher
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest

_ROOT = "run-raiz"
_POLICY = "d" * 64
_DOMAIN = "domain-a"


class _Solver:
    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.solve",
            description="generic test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"cut": inputs["cut"]}


def _store_con_raiz():
    store = create_event_store()
    store.append(
        stream_id=_ROOT,
        type="run.created",
        actor_id="user:dylan",
        domain_id=_DOMAIN,
        payload={
            "run_id": _ROOT,
            "actor_id": "user:dylan",
            "domain_id": _DOMAIN,
            "max_steps": 4,
            "policy_digest": _POLICY,
        },
    )
    return store


def _correr(store: Any, arms: list[AblationArm]) -> Any:
    return run_ablation_arms(
        store,
        EntryPointRegistry({"cap.solve": _Solver()}),
        ProfileDispatcher(),
        InMemoryContentStore(),
        root_run_id=_ROOT,
        root_policy_digest=_POLICY,
        actor_id="user:dylan",
        domain_id=_DOMAIN,
        arms=arms,
    )


_DOS_BRAZOS = [
    AblationArm(
        variant="quantum", capability_id="cap.solve", inputs={"cut": 5}, cut_cost=5.0
    ),
    AblationArm(
        variant="classical", capability_id="cap.solve", inputs={"cut": 7}, cut_cost=7.0
    ),
]


class TestCadaBrazoEsUnSubRun:
    def test_cada_brazo_tiene_su_propio_stream(self) -> None:
        store = _store_con_raiz()

        outcomes = _correr(store, _DOS_BRAZOS)

        assert [o.variant for o in outcomes] == ["quantum", "classical"]
        for outcome in outcomes:
            stream = store.read_stream(outcome.sub_run_id)
            assert stream[0].type == "run.created"
            assert stream[0].payload["parent_run_id"] == _ROOT

    def test_cada_brazo_cierra_con_su_propia_variante(self) -> None:
        store = _store_con_raiz()

        outcomes = _correr(store, _DOS_BRAZOS)

        for outcome in outcomes:
            metricas = [
                e
                for e in store.read_stream(outcome.sub_run_id)
                if e.type == "run.metrics.recorded"
            ]
            assert len(metricas) == 1
            assert metricas[0].payload["variant"] == outcome.variant
            assert metricas[0].payload["wall_ms"] > 0

    def test_el_costo_de_corte_lo_declara_el_experimento(self) -> None:
        """El log de verificación no conoce el costo de corte — lo declara
        quien corre el brazo, o el campo queda ausente."""
        store = _store_con_raiz()

        _correr(
            store,
            [
                AblationArm(
                    variant="quantum", capability_id="cap.solve", inputs={"cut": 5}
                )
            ],
        )

        payload = next(
            e.payload
            for e in store.read_stream(f"{_ROOT}--arm-0-quantum")
            if e.type == "run.metrics.recorded"
        )
        assert "cut_cost" not in payload


class TestHerenciaYProcedencia:
    def test_el_brazo_hereda_la_policy_del_raiz(self) -> None:
        store = _store_con_raiz()

        _correr(store, _DOS_BRAZOS[:1])

        creado = store.read_stream(f"{_ROOT}--arm-0-quantum")[0]
        assert creado.payload["policy_digest"] == _POLICY

    def test_ningun_brazo_puede_declarar_su_propia_policy(self) -> None:
        """§13 regla 3, garantizada POR CONSTRUCCIÓN: `AblationArm` no tiene
        campo de policy, así que un brazo no puede divergir ni por accidente.
        Comparar dos brazos bajo exigencias distintas no sería una ablación —
        sería medir dos cosas y llamarlas la misma."""
        assert not hasattr(AblationArm("quantum", "cap.solve", {}), "policy_digest")

        store = _store_con_raiz()
        _correr(store, _DOS_BRAZOS)

        digests = {
            store.read_stream(f"{_ROOT}--arm-{i}-{v}")[0].payload["policy_digest"]
            for i, v in enumerate(("quantum", "classical"))
        }
        assert digests == {_POLICY}

    def test_un_brazo_completado_aporta_su_hash_de_procedencia(self) -> None:
        store = _store_con_raiz()

        outcomes = _correr(store, _DOS_BRAZOS[:1])

        assert outcomes[0].status == "completed"
        assert outcomes[0].sub_run_provenance_hash is not None
        assert len(outcomes[0].sub_run_provenance_hash) == 64
