"""Registro instancia→verifiers — plan `docs/mvp/01-runtime-api.md` §3.

Fail-closed: CP-SAT ampara SIEMPRE un claim de optimalidad; pandapower se
añade solo cuando la instancia trae dato eléctrico (decisión #8, semilla
`sintetica-4bus`). Un `claim_type` fuera del vocabulario de optimalidad no
ampara verificación con nada — resolución vacía, señal para que el caller
devuelva 400 (decisión #7): jamás un run sin verificación.
"""

from __future__ import annotations

from chimera_api.instance_verifiers import resolve_verifiers

from blite.verification.exact_solver import ExactSolverVerifier
from blite.verification.execution import ExecutionVerifier


class TestClaimDeOptimalidadConDatoElectrico:
    def test_instancia_con_dato_electrico_ampara_dos_verifiers(self) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(
            claim_type="solution", instance_id="sintetica-4bus"
        )

        # Assert
        assert len(resolution.verifiers) == 2
        kinds = {d["kind"] for d in resolution.anchor_descriptors}
        assert kinds == {"solver", "execution"}
        assert resolution.verifiers[0].verifier_class == "formal_exact"
        assert resolution.verifiers[1].verifier_class == "execution"


class TestClaimDeOptimalidadSinDatoElectrico:
    def test_instancia_desconocida_ampara_solo_cpsat(self) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(
            claim_type="solution", instance_id="instancia-desconocida"
        )

        # Assert
        assert len(resolution.verifiers) == 1
        assert len(resolution.anchor_descriptors) == 1
        assert resolution.anchor_descriptors[0]["kind"] == "solver"
        assert resolution.verifiers[0].verifier_class == "formal_exact"


class TestClaimTypeNoOptimalidadFailCloses:
    def test_mystery_con_instancia_con_dato_electrico_da_vacio(self) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(
            claim_type="mystery", instance_id="sintetica-4bus"
        )

        # Assert — ni el dato eléctrico rescata un claim_type no amparado
        assert resolution.verifiers == ()
        assert resolution.anchor_descriptors == ()

    def test_mystery_con_instancia_desconocida_da_vacio(self) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(claim_type="mystery", instance_id="x")

        # Assert
        assert resolution.verifiers == ()
        assert resolution.anchor_descriptors == ()


class TestVerifiersRealesNoDobles:
    def test_la_resolucion_construye_adapters_reales_del_puerto_verifier(
        self,
    ) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(
            claim_type="solution", instance_id="sintetica-4bus"
        )

        # Assert — tipos reales del puerto Verifier, no dobles
        solver_verifier, execution_verifier = resolution.verifiers
        assert isinstance(solver_verifier, ExactSolverVerifier)
        assert isinstance(execution_verifier, ExecutionVerifier)

        # Properties del Protocol (verifier_id, anchor_kind, verifier_class)
        # expuestas por los adapters concretos que la resolución construyó.
        assert solver_verifier.verifier_id == "verifier:cpsat-differential"
        assert solver_verifier.anchor_kind == "solver"
        assert solver_verifier.verifier_class == "formal_exact"
        assert execution_verifier.verifier_id == "verifier:pandapower-islanding"
        assert execution_verifier.anchor_kind == "execution"
        assert execution_verifier.verifier_class == "execution"
