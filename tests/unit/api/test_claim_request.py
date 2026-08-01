"""`ClaimRequest` generalizado — `docs/specs/generalidad-retos.md`
§Contrato-6 Part 2: dos formas mutuamente excluyentes (`payload` XOR
`instance`+`assignment` legacy), normalizadas a un solo dict río abajo.
"""

from __future__ import annotations

import pytest
from chimera_api.runs import ClaimRequest, InstanceRequest
from pydantic import ValidationError

_CANONICAL_STATEMENT = "la partición propuesta es óptima"
_SCOPE = {"instancia": "sintetica-4bus"}


class TestFormaLegacy:
    def test_instance_y_assignment_validan(self) -> None:
        claim = ClaimRequest(
            instance=InstanceRequest(n_nodes=2, edges=((0, 1, 1),)),
            assignment=(0, 1),
            canonical_statement=_CANONICAL_STATEMENT,
            scope=_SCOPE,
            claim_type="solution",
        )

        assert claim.resolved_payload() == {
            "instance": {"n_nodes": 2, "edges": ((0, 1, 1),)},
            "assignment": [0, 1],
        }


class TestFormaPayload:
    def test_payload_solo_valida(self) -> None:
        payload = {"n_sites": 2, "terms": (), "time": 1.0}
        claim = ClaimRequest(
            payload=payload,
            canonical_statement=_CANONICAL_STATEMENT,
            scope=_SCOPE,
            claim_type="simulation_result",
        )

        assert claim.resolved_payload() == payload
        # resolved_payload() devuelve el MISMO objeto para la forma
        # payload — nada se reconstruye de más.
        assert claim.resolved_payload() is claim.payload


class TestFormasInvalidas:
    def test_ni_payload_ni_legacy_da_validation_error(self) -> None:
        with pytest.raises(ValidationError, match="exactamente una forma"):
            ClaimRequest(
                canonical_statement=_CANONICAL_STATEMENT,
                scope=_SCOPE,
                claim_type="solution",
            )

    def test_payload_y_legacy_juntos_da_validation_error(self) -> None:
        with pytest.raises(ValidationError, match="exactamente una forma"):
            ClaimRequest(
                instance=InstanceRequest(n_nodes=2, edges=((0, 1, 1),)),
                assignment=(0, 1),
                payload={"n_sites": 2},
                canonical_statement=_CANONICAL_STATEMENT,
                scope=_SCOPE,
                claim_type="solution",
            )

    def test_instance_sin_assignment_da_validation_error(self) -> None:
        with pytest.raises(ValidationError, match="deben venir JUNTOS"):
            ClaimRequest(
                instance=InstanceRequest(n_nodes=2, edges=((0, 1, 1),)),
                canonical_statement=_CANONICAL_STATEMENT,
                scope=_SCOPE,
                claim_type="solution",
            )

    def test_assignment_sin_instance_da_validation_error(self) -> None:
        with pytest.raises(ValidationError, match="deben venir JUNTOS"):
            ClaimRequest(
                assignment=(0, 1),
                canonical_statement=_CANONICAL_STATEMENT,
                scope=_SCOPE,
                claim_type="solution",
            )


class TestClaimRequestEsFrozen:
    def test_no_se_puede_mutar(self) -> None:
        claim = ClaimRequest(
            instance=InstanceRequest(n_nodes=2, edges=((0, 1, 1),)),
            assignment=(0, 1),
            canonical_statement=_CANONICAL_STATEMENT,
            scope=_SCOPE,
            claim_type="solution",
        )
        with pytest.raises(ValidationError):
            claim.claim_type = "tampered"
