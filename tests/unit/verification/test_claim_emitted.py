"""Portadores de `●ClaimEmitted` (freeze §6 [SF-P1-2 + stress-final]).

El claim carga `claim_type` (registro) + `is_conclusion` + los flags de piso
(`world`, `irreversible`, `affects_third_party`) en el MISMO payload — sin
esto el evaluador de la Policy 0.2.0 no es construible. La matriz casa por
criticidad COMPUTADA: conclusión ⇒ C3, intermedia ⇒ C1 (la re-expresión
solution/intermediate del YAML), y el piso por flags solo sube (PR2/PR4).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from blite.verification.claim import ClaimEmittedPayload, computed_criticality

DIGEST = "d" * 64


class TestPortadores:
    def test_carga_los_portadores_del_freeze(self) -> None:
        payload = ClaimEmittedPayload(
            claim_digest=DIGEST,
            claim_type="simulation_result",
            is_conclusion=True,
        )
        assert payload.is_conclusion is True
        assert payload.world is False  # flags de piso: default False, jamás implícitos

    def test_claim_digest_es_sha256_hex(self) -> None:
        with pytest.raises(ValidationError):
            ClaimEmittedPayload(
                claim_digest="no-es-digest", claim_type="solution", is_conclusion=False
            )

    def test_sub_run_provenance_hash_opcional(self) -> None:
        # Run jerárquico (freeze §13): el claim del sub-run viaja con su hash.
        payload = ClaimEmittedPayload(
            claim_digest=DIGEST,
            claim_type="solution",
            is_conclusion=True,
            sub_run_provenance_hash="a" * 64,
        )
        assert payload.sub_run_provenance_hash == "a" * 64

    def test_sub_run_id_opcional_correlaciona_con_el_hash(self) -> None:
        # freeze §13 regla 2: "el hash encadena, el id correlaciona" — ambos
        # campos son gemelos, uno solo no basta (A4).
        assert "sub_run_id" in ClaimEmittedPayload.model_fields
        payload = ClaimEmittedPayload(
            claim_digest=DIGEST,
            claim_type="solution",
            is_conclusion=True,
            sub_run_id="run-sub-1",
            sub_run_provenance_hash="a" * 64,
        )
        assert payload.sub_run_id == "run-sub-1"
        assert payload.sub_run_provenance_hash == "a" * 64

    def test_sub_run_id_es_none_por_defecto(self) -> None:
        payload = ClaimEmittedPayload(
            claim_digest=DIGEST, claim_type="solution", is_conclusion=True
        )
        assert payload.sub_run_id is None


class TestCriticidadComputada:
    def test_conclusion_es_c3_intermedia_es_c1(self) -> None:
        conclusion = ClaimEmittedPayload(
            claim_digest=DIGEST, claim_type="solution", is_conclusion=True
        )
        intermediate = ClaimEmittedPayload(
            claim_digest=DIGEST, claim_type="intermediate", is_conclusion=False
        )
        assert computed_criticality(conclusion) == "C3"
        assert computed_criticality(intermediate) == "C1"

    def test_world_sube_el_piso_a_c2(self) -> None:
        payload = ClaimEmittedPayload(
            claim_digest=DIGEST,
            claim_type="intermediate",
            is_conclusion=False,
            world=True,
        )
        assert computed_criticality(payload) == "C2"

    def test_irreversible_con_terceros_es_c3(self) -> None:
        payload = ClaimEmittedPayload(
            claim_digest=DIGEST,
            claim_type="intermediate",
            is_conclusion=False,
            irreversible=True,
            affects_third_party=True,
        )
        assert computed_criticality(payload) == "C3"

    def test_el_piso_jamas_baja_una_conclusion(self) -> None:
        payload = ClaimEmittedPayload(
            claim_digest=DIGEST, claim_type="solution", is_conclusion=True, world=True
        )
        assert computed_criticality(payload) == "C3"
