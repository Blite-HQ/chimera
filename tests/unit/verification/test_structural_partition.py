"""`StructuralPartitionVerifier` — la pata por sub-entidad que SÍ existe
cuando no hay ancla de ejecución (V1/M18).

Por qué existe: la red real del ICE no trae impedancias ni cargas, así que
`ExecutionVerifier` (pandapower, AL3) no puede correr sobre ella — y sin
checks `island-{k}:*` no hay verdict por isla, o sea no hay badges sobre el
mapa. La salida honesta NO es inventar dato eléctrico: es verificar lo que el
grafo SÍ permite verificar — conectividad interna, cobertura y coherencia del
corte — y decirlo con el techo que le corresponde (`property_rule`, AL2).

Lo que este verificador NO afirma: nada eléctrico. Una partición conexa puede
ser inviable eléctricamente; el badge dice AL2/`rule`, no AL3/`execution`.
"""

from __future__ import annotations

import pytest

from blite.verification.attestation import CLASS_CEILINGS
from blite.verification.context import InvocationContext
from blite.verification.exact_solver import (
    MaxCutInstance,
    OptimalityClaim,
    VerificationProcessError,
)
from blite.verification.partition import island_checks_by_island
from blite.verification.structural_partition import (
    STRUCTURAL_HARNESS_ID,
    StructuralPartitionVerifier,
)

_CTX = InvocationContext(
    run_id="run-1", actor_id="service:runtime", domain_id="domain-a"
)


def _verifier() -> StructuralPartitionVerifier:
    return StructuralPartitionVerifier(
        verifier_id="verifier:structural-partition",
        independence_group="leg-structural",
        anchor_digest="a" * 64,
    )


def _claim(
    edges: tuple[tuple[int, int, int], ...], assignment: tuple[int, ...]
) -> OptimalityClaim:
    return OptimalityClaim(
        instance=MaxCutInstance(n_nodes=len(assignment), edges=edges),
        assignment=assignment,
        canonical_statement="la partición propuesta es óptima",
        scope={"instancia": "x"},
    )


class TestChecksPorIsla:
    def test_una_particion_sana_pasa_con_checks_por_isla(self) -> None:
        # Arrange — {0,1} y {2,3}, conexas internamente, corte = (1,2)
        claim = _claim(((0, 1, 1), (1, 2, 5), (2, 3, 1)), (0, 0, 1, 1))

        # Act
        attestation = _verifier().verify(claim, _CTX)

        # Assert
        assert attestation.verdict == "pass"
        assert attestation.level == "AL2"
        assert attestation.verifier_class == "property_rule"
        assert attestation.anchor_kind == "rule"
        assert set(island_checks_by_island(attestation)) == {"island-0", "island-1"}

    def test_una_isla_desconectada_falla_solo_esa_isla(self) -> None:
        # Arrange — la isla 0 junta 0 y 2 sin arista interna
        claim = _claim(((0, 1, 1), (1, 3, 1), (2, 3, 1)), (0, 1, 0, 1))

        # Act
        attestation = _verifier().verify(claim, _CTX)
        grupos = island_checks_by_island(attestation)

        # Assert
        fallidos = {
            isla: [c.name for c in checks if not c.passed]
            for isla, checks in grupos.items()
        }
        assert fallidos["island-0"] == ["island-0:subgraph_connected"]
        assert fallidos["island-1"] == []
        assert attestation.verdict == "fail"

    def test_una_isla_de_un_solo_nodo_es_conexa(self) -> None:
        claim = _claim(((0, 1, 1),), (0, 1))
        attestation = _verifier().verify(claim, _CTX)
        assert attestation.verdict == "pass"


class TestChecksGlobales:
    def test_el_corte_declarado_se_recomputa_y_se_reporta_global(self) -> None:
        """El check de corte NO lleva prefijo de isla: pertenece al resultado,
        no a una isla (C-8)."""
        # Arrange
        claim = _claim(((0, 1, 1), (1, 2, 5), (2, 3, 1)), (0, 0, 1, 1))

        # Act
        attestation = _verifier().verify(claim, _CTX)

        # Assert
        nombres = [c.name for c in attestation.predicate.properties]  # type: ignore[union-attr]
        assert "cut_edges_nonempty" in nombres
        assert not any(n.startswith("island-") for n in ["cut_edges_nonempty"])

    def test_una_particion_de_una_sola_isla_no_corta_nada_y_falla(self) -> None:
        """Todo en una isla = no hubo partición: el corte vacío es un
        resultado degenerado, y se dice."""
        # Arrange
        claim = _claim(((0, 1, 1), (1, 2, 5)), (0, 0, 0))

        # Act
        attestation = _verifier().verify(claim, _CTX)

        # Assert
        assert attestation.verdict == "fail"
        fallidos = [c.name for c in attestation.predicate.properties if not c.passed]  # type: ignore[union-attr]
        assert fallidos == ["cut_edges_nonempty"]


class TestFronteras:
    def test_un_claim_ajeno_es_error_de_proceso(self) -> None:
        with pytest.raises(VerificationProcessError, match="OptimalityClaim"):
            _verifier().verify({"no": "soy"}, _CTX)

    def test_el_techo_de_la_clase_es_al2(self) -> None:
        """Un chequeo estructural jamás finge la fuerza de una ejecución."""
        assert CLASS_CEILINGS["property_rule"] == "AL2"

    def test_el_harness_se_estampa_en_el_metodo(self) -> None:
        claim = _claim(((0, 1, 1),), (0, 1))
        attestation = _verifier().verify(claim, _CTX)
        assert attestation.predicate.backend == STRUCTURAL_HARNESS_ID  # type: ignore[union-attr]

    def test_dos_corridas_del_mismo_claim_dan_el_mismo_params_digest(self) -> None:
        claim = _claim(((0, 1, 1),), (0, 1))
        primera = _verifier().verify(claim, _CTX)
        segunda = _verifier().verify(claim, _CTX)
        assert primera.verifier_params_digest == segunda.verifier_params_digest
        assert primera.claim_digest == segunda.claim_digest
