"""`verify_all()` y la attestation POR ISLA — ítem C4/M4 (C-6/#106, freeze §7).

La regla que este archivo hace cumplir, y que es la razón de ser del ítem:
**las attestations por isla de una MISMA corrida comparten
`independence_group` — jamás inflan patas.** Sin ella, partir un verdict
global en N verdicts por isla convertiría un verificador en N «patas
independientes» y una conclusión C3 (2 patas exigidas) pasaría con UNA sola
fuente de evidencia. La granularidad fina es para EXPLICAR, no para
multiplicar respaldo.

Convención heredada de S-D (#125, `docs/specs/superficie-visual.md` §8): el
verdict de la isla `k` = `derive_execution_verdict` sobre el SUBCONJUNTO de
checks `island-{k}:*` de esa isla, y `step_id = island_id` estable
(`island-{k}`).
"""

from __future__ import annotations

from typing import Any

from blite.verification.attestation import Attestation
from blite.verification.evidence import ExecutionPredicate
from blite.verification.verifier import Verifier, verify_all_of
from tests.unit.verification.test_execution_verifier import (
    CTX,
    FEASIBLE_TOPOLOGY,
    claim_for,
    make_verifier,
)

# Misma red de 4 buses, pero la rama interna de la isla {2,3} desaparece: la
# partición {0,1}|{2,3} deja la segunda isla DESCONECTADA. La primera sigue
# sana — el caso donde un verdict global («fail») esconde que la mitad del
# resultado sí se sostiene.
TOPOLOGY_UNA_ISLA_ROTA: dict[str, Any] = {
    **FEASIBLE_TOPOLOGY,
    "branches": [
        {"from": 0, "to": 1, "r_ohm_per_km": 0.05, "x_ohm_per_km": 0.1},
        {"from": 1, "to": 2, "r_ohm_per_km": 0.05, "x_ohm_per_km": 0.1},
    ],
}


def _islas(attestations: tuple[Attestation, ...]) -> dict[str | None, Attestation]:
    return {att.step_id: att for att in attestations}


# ── El default del puerto: compat total ─────────────────────────────────


def test_un_adapter_que_solo_implementa_verify_hereda_el_default() -> None:
    """C-6: `verify_all()` con default `= (verify(),)`. Todo adapter
    existente sigue funcionando sin tocarlo — la extensión del puerto no
    puede exigir que 6 adapters se reescriban el mismo día."""

    class _Uno(Verifier):
        @property
        def verifier_class(self) -> Any:
            return "ground_truth"

        @property
        def anchor_kind(self) -> Any:
            return "dataset"

        @property
        def determinism(self) -> Any:
            return "deterministic"

        def verify(self, claim: Any, ctx: Any) -> Any:
            return "CONSTANCIA"

    assert _Uno().verify_all({"claim": True}, CTX) == ("CONSTANCIA",)


def test_el_helper_cubre_a_los_adapters_estructurales() -> None:
    """Los adapters del repo satisfacen `Verifier` ESTRUCTURALMENTE (frozen
    dataclasses que no heredan del Protocol), así que no heredan el cuerpo
    del default: el llamador usa `verify_all_of`, que es la misma regla
    aplicada desde afuera. Sin este helper, «compat total» sería falso
    justo para los adapters que existen."""

    class _Estructural:
        def verify(self, claim: Any, ctx: Any) -> str:
            return "CONSTANCIA"

    assert verify_all_of(_Estructural(), None, CTX) == ("CONSTANCIA",)


def test_el_helper_prefiere_verify_all_cuando_el_adapter_lo_implementa() -> None:
    class _Multiple:
        def verify(self, claim: Any, ctx: Any) -> str:
            return "GLOBAL"

        def verify_all(self, claim: Any, ctx: Any) -> tuple[str, ...]:
            return ("A", "B")

    assert verify_all_of(_Multiple(), None, CTX) == ("A", "B")


# ── ExecutionVerifier: una constancia por isla ──────────────────────────


def test_verify_all_emite_una_constancia_por_isla_con_step_id_estable() -> None:
    """`step_id = island_id` (`island-{k}`) — S-D §8. Estable: el mismo
    resultado produce el mismo id en cada corrida, o el mapa no podría
    atar un badge a su isla entre refrescos."""
    # Act
    attestations = make_verifier().verify_all(claim_for((0, 0, 1, 1)), CTX)

    # Assert
    assert [att.step_id for att in attestations] == ["island-0", "island-1"]


def test_cada_constancia_lleva_solo_los_checks_de_su_isla() -> None:
    """«Ningún check de otra isla contamina» (S-D §8): si la evidencia de la
    isla 1 viaja dentro de la constancia de la isla 0, el verdict por isla es
    decorativo."""
    # Act
    attestations = make_verifier().verify_all(claim_for((0, 0, 1, 1)), CTX)

    # Assert
    for att in attestations:
        predicate = att.predicate
        assert isinstance(predicate, ExecutionPredicate)
        assert predicate.checks
        assert all(
            check.name.startswith(f"{att.step_id}:") for check in predicate.checks
        )


def test_todas_las_islas_de_una_corrida_comparten_independence_group() -> None:
    """LA regla de C-6. Partir un verdict en N no crea N patas: sigue siendo
    un verificador, un ancla, una fuente de evidencia."""
    # Act
    attestations = make_verifier().verify_all(claim_for((0, 0, 1, 1)), CTX)

    # Assert
    assert len({att.independence_group for att in attestations}) == 1
    assert len(attestations) > 1  # o la aserción de arriba sería vacua


def test_una_isla_rota_falla_sin_arrastrar_a_la_isla_sana() -> None:
    """El valor real de la granularidad: el verdict global dice «fail» y no
    dice DÓNDE. Con constancia por isla, la isla sana conserva su `pass` y el
    auditor ve exactamente cuál se cayó."""
    # Arrange
    verifier = make_verifier(topology=TOPOLOGY_UNA_ISLA_ROTA)

    # Act
    por_isla = _islas(verifier.verify_all(claim_for((0, 0, 1, 1)), CTX))
    global_ = verifier.verify(claim_for((0, 0, 1, 1)), CTX)

    # Assert
    assert global_.verdict == "fail"
    assert por_isla["island-0"].verdict == "pass"
    assert por_isla["island-1"].verdict == "fail"


def test_la_constancia_por_isla_respeta_el_techo_de_su_clase() -> None:
    """Un `fail`/`pass` por isla es `execution` AL3 como cualquier otra
    constancia de la clase; una isla `inconclusive` cae a AL0 (mismo mapeo
    que el camino global — la granularidad no cambia la fuerza)."""
    attestations = make_verifier().verify_all(claim_for((0, 0, 1, 1)), CTX)

    for att in attestations:
        assert att.verifier_class == "execution"
        assert att.level == "AL3"
        assert att.verdict == "pass"


def test_todas_las_constancias_comparten_claim_y_binding() -> None:
    """Las islas son vistas del MISMO claim: si cada una trajera su propio
    `claim_digest`, el punto 7 del checklist no encontraría ninguna
    attestation que sostenga la conclusión."""
    # Act
    attestations = make_verifier().verify_all(claim_for((0, 0, 1, 1)), CTX)
    global_ = make_verifier().verify(claim_for((0, 0, 1, 1)), CTX)

    # Assert
    assert {att.claim_digest for att in attestations} == {global_.claim_digest}
    assert {att.anchor_digest for att in attestations} == {global_.anchor_digest}
    assert {att.verifier_params_digest for att in attestations} == {
        global_.verifier_params_digest
    }


def test_verify_sigue_emitiendo_la_constancia_global_intacta() -> None:
    """Compat: `verify()` no cambia de forma. Los llamadores que ya existen
    (y los bundles ya emitidos) siguen viendo exactamente lo mismo."""
    # Act
    att = make_verifier().verify(claim_for((0, 0, 1, 1)), CTX)
    predicate = att.predicate

    # Assert
    assert att.step_id is None
    assert isinstance(predicate, ExecutionPredicate)
    assert {check.name.split(":")[0] for check in predicate.checks} == {
        "island-0",
        "island-1",
    }
