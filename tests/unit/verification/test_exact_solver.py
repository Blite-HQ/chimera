"""ExactSolverVerifier (CP-SAT) — el primer adapter real del puerto Verifier.

Nota 10 (knowledge/trust/10): verificación diferencial rung-1 → clase
`formal_exact`. Los vectores G1–G6 son óptimos calculados A MANO (§1.6) y son
el gate de entrada: la implementación que no los reproduzca no entra. El mapeo
status→verdict (§1.2) se prueba directo sobre la función pura; el camino
end-to-end sobre CP-SAT real. La falla sembrada de ieee14 (convergencia EC-2)
queda como regresión: fail inequívoco, jamás inconclusive.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from blite.certificate.canonical import JSONValue, canonicalize
from blite.verification.attestation import Attestation
from blite.verification.context import InvocationContext
from blite.verification.evidence import Differential, FormalExactPredicate
from blite.verification.exact_solver import (
    ExactSolverVerifier,
    MaxCutInstance,
    OptimalityClaim,
    VerificationProcessError,
    map_optimality_verdict,
)

CORPUS = Path(__file__).parents[3] / "knowledge" / "islanding" / "corpus"

CTX = InvocationContext(
    run_id="run:test", actor_id="service:runtime", domain_id="dom:test"
)

ANCHOR_DIGEST = hashlib.sha256(b"anchor:cpsat-reference-v1").hexdigest()


class CorpusIeee14(BaseModel):
    """Vista tipada del fixture del corpus — solo los campos que usa el test."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    aristas: tuple[tuple[int, int, int], ...]
    asignacion_canonica: tuple[int, ...]
    n_nodos: int
    optimo: int


def make_verifier() -> ExactSolverVerifier:
    return ExactSolverVerifier(
        verifier_id="verifier:cpsat-differential",
        independence_group="leg-formal",
        anchor_digest=ANCHOR_DIGEST,
    )


def claim_for(
    edges: tuple[tuple[int, int, int], ...],
    n_nodes: int,
    assignment: tuple[int, ...],
    claimed: int | None = None,
) -> OptimalityClaim:
    return OptimalityClaim(
        instance=MaxCutInstance(n_nodes=n_nodes, edges=edges),
        assignment=assignment,
        claimed_objective=claimed,
        canonical_statement="la asignación propuesta es el corte máximo exacto",
        scope={"instancia": "vector-de-prueba"},
    )


def differential_of(att: Attestation) -> Differential:
    """Narrowing del union ClassPredicate a la evidencia formal_exact."""
    assert isinstance(att.predicate, FormalExactPredicate)
    return att.predicate.differential


K3 = ((0, 1, 1), (1, 2, 1), (0, 2, 1))


class TestVectoresAMano:
    """§1.6 — pesos unitarios salvo G6; asignaciones canónicas (x_0 = 0)."""

    def test_g1_triangulo_optimo_pasa(self) -> None:
        att = make_verifier().verify(claim_for(K3, 3, (0, 0, 1)), CTX)

        assert att.verdict == "pass"
        diff = differential_of(att)
        assert diff.status == "OPTIMAL"
        assert diff.objective == 2
        assert diff.reference_objective == 2
        assert att.level == "AL3"  # formal_exact sin proof (freeze §4)
        assert att.anchor_digest == ANCHOR_DIGEST

    def test_g1_suboptimo_falla(self) -> None:
        att = make_verifier().verify(claim_for(K3, 3, (0, 0, 0)), CTX)

        assert att.verdict == "fail"
        assert differential_of(att).objective == 0
        assert differential_of(att).reference_objective == 2

    def test_g2_ciclo_c4_bipartito_corta_todas(self) -> None:
        c4 = ((0, 1, 1), (1, 2, 1), (2, 3, 1), (3, 0, 1))
        att = make_verifier().verify(claim_for(c4, 4, (0, 1, 0, 1)), CTX)

        assert att.verdict == "pass"
        assert differential_of(att).reference_objective == 4

    def test_g2_suboptimo_falla_con_gap_2(self) -> None:
        c4 = ((0, 1, 1), (1, 2, 1), (2, 3, 1), (3, 0, 1))
        att = make_verifier().verify(claim_for(c4, 4, (0, 0, 1, 1)), CTX)

        assert att.verdict == "fail"
        assert differential_of(att).objective == 2
        assert differential_of(att).reference_objective == 4

    def test_g3_k4_split_dos_dos_pasa(self) -> None:
        k4 = ((0, 1, 1), (0, 2, 1), (0, 3, 1), (1, 2, 1), (1, 3, 1), (2, 3, 1))
        att = make_verifier().verify(claim_for(k4, 4, (0, 0, 1, 1)), CTX)

        assert att.verdict == "pass"
        assert differential_of(att).reference_objective == 4

    def test_g4_camino_p3_pasa(self) -> None:
        p3 = ((0, 1, 1), (1, 2, 1))
        att = make_verifier().verify(claim_for(p3, 3, (0, 1, 0)), CTX)

        assert att.verdict == "pass"
        assert differential_of(att).reference_objective == 2

    def test_g5_nodo_aislado_no_cambia_el_optimo(self) -> None:
        # Metamórfica (nota 03): K3 + nodo 3 aislado — óptimo sigue en 2
        att = make_verifier().verify(claim_for(K3, 4, (0, 0, 1, 0)), CTX)

        assert att.verdict == "pass"
        assert differential_of(att).reference_objective == 2

    def test_g6_triangulo_pesado_aisla_el_nodo_dos(self) -> None:
        g6 = ((0, 1, 1), (1, 2, 2), (0, 2, 3))
        att = make_verifier().verify(claim_for(g6, 3, (0, 0, 1)), CTX)

        assert att.verdict == "pass"
        assert differential_of(att).objective == 5
        assert differential_of(att).reference_objective == 5

    def test_g7_peso_negativo_el_optimo_evita_la_arista_penalizada(self) -> None:
        # A mano: {2}|{0,1} corta (1,2)+(0,2) = 2+2 = 4 (máximo);
        # {0} o {1} solos cortan la arista negativa: -1+2 = 1.
        # Candado de la propiedad "agnóstico al signo" (4 restricciones §1.5).
        g7 = ((0, 1, -1), (1, 2, 2), (0, 2, 2))
        att = make_verifier().verify(claim_for(g7, 3, (0, 0, 1)), CTX)

        assert att.verdict == "pass"
        assert differential_of(att).objective == 4
        assert differential_of(att).reference_objective == 4

    def test_g7_peso_negativo_cortar_la_arista_penalizada_falla(self) -> None:
        g7 = ((0, 1, -1), (1, 2, 2), (0, 2, 2))
        att = make_verifier().verify(claim_for(g7, 3, (0, 1, 0)), CTX)

        assert att.verdict == "fail"
        assert differential_of(att).objective == 1  # -1 + 2
        assert differential_of(att).reference_objective == 4


class TestCasosNegativos:
    def test_energia_mentida_falla_aunque_la_asignacion_sea_optima(self) -> None:
        # §1.1 paso 1: el recompute desmiente el número reportado ⇒ fail,
        # sin importar que la asignación en sí sea el óptimo real.
        att = make_verifier().verify(claim_for(K3, 3, (0, 0, 1), claimed=3), CTX)

        assert att.verdict == "fail"
        assert differential_of(att).objective == 2  # la verdad recomputada

    def test_energia_honesta_explicita_pasa(self) -> None:
        att = make_verifier().verify(claim_for(K3, 3, (0, 0, 1), claimed=2), CTX)

        assert att.verdict == "pass"

    def test_asignacion_de_largo_invalido_levanta_no_falla(self) -> None:
        # Error de proceso ≠ fail: input malformado jamás se disfraza de verdict
        with pytest.raises(ValidationError):
            claim_for(K3, 3, (0, 0))

    def test_asignacion_no_binaria_levanta(self) -> None:
        with pytest.raises(ValidationError):
            claim_for(K3, 3, (0, 0, 2))


class TestMapeoStatusVerdict:
    """§1.2 — la tabla exacta, sobre la función pura (sin solver)."""

    def test_optimal_igual_es_pass(self) -> None:
        assert map_optimality_verdict("OPTIMAL", candidate=2, reference=2) == "pass"

    def test_optimal_peor_es_fail(self) -> None:
        assert map_optimality_verdict("OPTIMAL", candidate=0, reference=2) == "fail"

    def test_optimal_candidato_mejor_es_contradiccion_fail_loud(self) -> None:
        # CP-SAT PROBÓ el máximo; un valor mejor ⇒ el modelo del verificador
        # difiere del objetivo real. Jamás pass silencioso.
        with pytest.raises(VerificationProcessError):
            map_optimality_verdict("OPTIMAL", candidate=3, reference=2)

    def test_feasible_es_inconclusive_para_optimalidad(self) -> None:
        # Timeout con incumbente: es cota, no ancla (§1.3)
        assert (
            map_optimality_verdict("FEASIBLE", candidate=2, reference=2)
            == "inconclusive"
        )

    def test_unknown_es_inconclusive(self) -> None:
        assert (
            map_optimality_verdict("UNKNOWN", candidate=2, reference=0)
            == "inconclusive"
        )

    def test_infeasible_es_error_de_proceso(self) -> None:
        # Hay un candidato en mano ⇒ el problema NO es infactible: bug de modelado
        with pytest.raises(VerificationProcessError):
            map_optimality_verdict("INFEASIBLE", candidate=2, reference=0)

    def test_model_invalid_es_error_de_proceso(self) -> None:
        with pytest.raises(VerificationProcessError):
            map_optimality_verdict("MODEL_INVALID", candidate=2, reference=0)


class TestCorpusIeee14:
    """El caso del demo (P0 freeze §15.4) como regresión permanente."""

    @pytest.fixture(scope="class")
    def corpus(self) -> CorpusIeee14:
        return CorpusIeee14.model_validate_json(
            (CORPUS / "ieee14-flujo.json").read_text()
        )

    def test_asignacion_canonica_es_el_optimo_57070(self, corpus: CorpusIeee14) -> None:
        claim = claim_for(corpus.aristas, corpus.n_nodos, corpus.asignacion_canonica)

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "pass"
        assert differential_of(att).reference_objective == 57_070
        assert corpus.optimo == 57_070  # el corpus y el ancla coinciden

    def test_falla_sembrada_bus_1_es_fail_inequivoco(
        self, corpus: CorpusIeee14
    ) -> None:
        # Convergencia EC-2: flip del bus 1 ⇒ corte 32 597 vs óptimo 57 070.
        # Criterio congelado (P0 #4): fail inequívoco, JAMÁS inconclusive.
        seeded = tuple(
            (1 - x) if i == 1 else x for i, x in enumerate(corpus.asignacion_canonica)
        )
        claim = claim_for(corpus.aristas, corpus.n_nodos, seeded)

        att = make_verifier().verify(claim, CTX)

        assert att.verdict == "fail"
        assert differential_of(att).objective == 32_597
        assert differential_of(att).reference_objective == 57_070


class TestDeterminismoYForma:
    """§1.4 — reproducible byte-a-byte; digests replayables."""

    def test_dos_corridas_identicas_salvo_issued_at(self) -> None:
        verifier = make_verifier()
        claim = claim_for(K3, 3, (0, 0, 1))

        a = verifier.verify(claim, CTX).model_dump(exclude={"issued_at"})
        b = verifier.verify(claim, CTX).model_dump(exclude={"issued_at"})

        assert a == b

    def test_claim_digest_sigue_la_convencion_del_anexo(self) -> None:
        claim = claim_for(K3, 3, (0, 0, 1))
        att = make_verifier().verify(claim, CTX)

        view: dict[str, JSONValue] = {
            "canonical_statement": claim.canonical_statement,
            "scope": claim.scope,
        }
        expected = hashlib.sha256(b"blite/claim/v1\n" + canonicalize(view)).hexdigest()
        assert att.claim_digest == expected

    def test_atributos_del_puerto(self) -> None:
        verifier = make_verifier()

        assert verifier.verifier_class == "formal_exact"
        assert verifier.anchor_kind == "solver"
        assert verifier.determinism == "deterministic"

    def test_contexto_viaja_al_attestation(self) -> None:
        att = make_verifier().verify(claim_for(K3, 3, (0, 0, 1)), CTX)

        assert att.run_id == "run:test"
        assert att.independence_group == "leg-formal"
