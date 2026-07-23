"""ExecutionVerifier (pandapower) — el adapter rung-2 del puerto Verifier.

Nota 12 (knowledge/trust/12 §1.3): "correr de verdad y observar, no opinar".
Checks por isla propuesta: conectividad, fuente, convergencia del flujo,
banda de voltaje, carga de líneas, y balance (si el límite existe como dato).
Reglas duras de la spec: no-convergencia ⇒ `inconclusive` (jamás `fail`);
verdict derivado (todos pass → pass; algún hard-fail → fail; inconclusive
sin hard-fail → inconclusive); topología y límites son DATOS del ancla, no
hardcode (regla "reglas como datos").

Los tests usan redes sintéticas chicas con desenlaces calculables a mano —
los datos eléctricos de ieee14 son dato de dominio (Sebas) y viven aparte.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from blite.verification.context import InvocationContext
from blite.verification.evidence import ExecutionPredicate
from blite.verification.exact_solver import (
    MaxCutInstance,
    OptimalityClaim,
    VerificationProcessError,
)
from blite.verification.execution import (
    ExecutionLimits,
    ExecutionVerifier,
    derive_execution_verdict,
)

CTX = InvocationContext(
    run_id="run-exec", actor_id="service:runtime", domain_id="dom-test"
)

ANCHOR_DIGEST = hashlib.sha256(b"anchor:pandapower-sintetica-v1").hexdigest()

# Red sintética de 4 buses: dos islas naturales {0,1} y {2,3} unidas por la
# rama (1,2). Cada isla tiene su fuente (slack) y una carga chica — el flujo
# converge holgado, voltajes ~1.0, cargas de línea mínimas.
FEASIBLE_TOPOLOGY: dict[str, Any] = {
    "buses": [{"id": i, "vn_kv": 20.0} for i in range(4)],
    "slack": [{"bus": 0, "vm_pu": 1.0}, {"bus": 2, "vm_pu": 1.0}],
    "branches": [
        {"from": 0, "to": 1, "r_ohm_per_km": 0.05, "x_ohm_per_km": 0.1},
        {"from": 2, "to": 3, "r_ohm_per_km": 0.05, "x_ohm_per_km": 0.1},
        {"from": 1, "to": 2, "r_ohm_per_km": 0.05, "x_ohm_per_km": 0.1},
    ],
    "loads": [
        {"bus": 1, "p_mw": 1.0},
        {"bus": 3, "p_mw": 1.0},
    ],
}

# El grafo combinatorio del claim (pesos ficticios — el ExecutionVerifier no
# los usa; verifica la FACTIBILIDAD de la partición, no su optimalidad).
GRAPH = MaxCutInstance(n_nodes=4, edges=((0, 1, 1), (2, 3, 1), (1, 2, 5)))


def claim_for(assignment: tuple[int, ...]) -> OptimalityClaim:
    return OptimalityClaim(
        instance=GRAPH,
        assignment=assignment,
        canonical_statement="la partición propuesta es electricamente factible",
        scope={"instancia": "sintetica-4bus"},
    )


def make_verifier(
    topology: dict[str, Any] | None = None,
    limits: ExecutionLimits | None = None,
) -> ExecutionVerifier:
    return ExecutionVerifier(
        verifier_id="verifier:pandapower-islanding",
        independence_group="leg-execution",
        anchor_digest=ANCHOR_DIGEST,
        topology=topology if topology is not None else FEASIBLE_TOPOLOGY,
        limits=limits if limits is not None else ExecutionLimits(),
    )


def predicate_of(att: Any) -> ExecutionPredicate:
    assert isinstance(att.predicate, ExecutionPredicate)
    return att.predicate


class TestCasoFactible:
    def test_particion_factible_pasa_con_checks_por_isla(self) -> None:
        att = make_verifier().verify(claim_for((0, 0, 1, 1)), CTX)

        assert att.verdict == "pass"
        assert att.level == "AL3"  # techo de la clase execution
        assert att.verifier_class == "execution"
        assert att.anchor_kind == "execution"
        pred = predicate_of(att)
        names = {c.name for c in pred.checks}
        # granularidad por isla: cada check viaja prefijado
        assert "island-0:island_connectivity" in names
        assert "island-1:powerflow_converged" in names
        assert "island-0:voltage_limits" in names
        assert all(c.passed for c in pred.checks)
        assert pred.environment.package == "pandapower"

    def test_el_predicate_lleva_harness_y_digest_de_input(self) -> None:
        att = make_verifier().verify(claim_for((0, 0, 1, 1)), CTX)

        pred = predicate_of(att)
        assert pred.harness == "pandapower-islanding-v1"
        assert len(pred.input_digest) == 64
        assert pred.runtime_ms >= 0


class TestHardFails:
    def test_isla_sin_fuente_falla(self) -> None:
        # Solo la isla {0,1} tiene slack; {2,3} queda sin fuente ⇒ fail
        topology = {
            **FEASIBLE_TOPOLOGY,
            "slack": [{"bus": 0, "vm_pu": 1.0}],
        }
        att = make_verifier(topology=topology).verify(claim_for((0, 0, 1, 1)), CTX)

        assert att.verdict == "fail"
        pred = predicate_of(att)
        failed = {c.name for c in pred.checks if not c.passed}
        assert "island-1:island_has_source" in failed

    def test_isla_internamente_desconectada_falla(self) -> None:
        # Partición (0,1,0,1): la isla {0,2} no tiene rama interna ⇒ inconexa
        att = make_verifier().verify(claim_for((0, 1, 0, 1)), CTX)

        assert att.verdict == "fail"
        pred = predicate_of(att)
        failed = {c.name for c in pred.checks if not c.passed}
        assert any(name.endswith("island_connectivity") for name in failed)

    def test_linea_sobrecargada_falla(self) -> None:
        # max_i_ka microscópico en la rama interna de la isla 0 ⇒ loading >> 100%
        topology = {
            **FEASIBLE_TOPOLOGY,
            "branches": [
                {
                    "from": 0,
                    "to": 1,
                    "r_ohm_per_km": 0.05,
                    "x_ohm_per_km": 0.1,
                    "max_i_ka": 0.0001,
                },
                {"from": 2, "to": 3, "r_ohm_per_km": 0.05, "x_ohm_per_km": 0.1},
                {"from": 1, "to": 2, "r_ohm_per_km": 0.05, "x_ohm_per_km": 0.1},
            ],
        }
        att = make_verifier(topology=topology).verify(claim_for((0, 0, 1, 1)), CTX)

        assert att.verdict == "fail"
        pred = predicate_of(att)
        failed = {c.name for c in pred.checks if not c.passed}
        assert "island-0:line_loading" in failed


class TestInconclusive:
    def test_no_convergencia_es_inconclusive_jamas_fail(self) -> None:
        # Carga absurda: el flujo de la isla 0 no converge ⇒ inconclusive
        topology = {
            **FEASIBLE_TOPOLOGY,
            "loads": [
                {"bus": 1, "p_mw": 1e6},
                {"bus": 3, "p_mw": 1.0},
            ],
        }
        att = make_verifier(topology=topology).verify(claim_for((0, 0, 1, 1)), CTX)

        assert att.verdict == "inconclusive"
        assert att.inconclusive_reason == "undecidable"
        assert att.level == "AL0"


class TestDerivacionDeVerdict:
    """La regla exacta de la spec §1.3, sobre la función pura."""

    def test_todos_pass_es_pass(self) -> None:
        assert derive_execution_verdict(all_passed=True, any_inconclusive=False) == (
            "pass"
        )

    def test_hard_fail_gana_sobre_inconclusive(self) -> None:
        assert derive_execution_verdict(all_passed=False, any_inconclusive=True) == (
            "fail"
        )

    def test_inconclusive_sin_hard_fail_es_inconclusive(self) -> None:
        assert derive_execution_verdict(all_passed=True, any_inconclusive=True) == (
            "inconclusive"
        )


class TestErroresDeProceso:
    def test_asignacion_que_no_casa_con_la_topologia_levanta(self) -> None:
        claim = OptimalityClaim(
            instance=MaxCutInstance(n_nodes=3, edges=((0, 1, 1), (1, 2, 1))),
            assignment=(0, 0, 1),
            canonical_statement="claim de otra red",
            scope={"instancia": "otra"},
        )
        with pytest.raises(VerificationProcessError):
            make_verifier().verify(claim, CTX)

    def test_claim_de_tipo_ajeno_levanta(self) -> None:
        with pytest.raises(VerificationProcessError):
            make_verifier().verify({"no": "es un claim"}, CTX)
