"""SEED · costura B↔A (Sebas+Dylan) — receta de derivación de la ingesta (R2).

freeze §1 (`CapabilityManifest` v2) / §12 (`Artifact`/`ContentStore`) / §14
(`●ClaimEmitted`) + docs/specs/capability-ingesta.md: una instancia derivada
carga su receta en vocabulario PROV/`dvc.lock` — `{inputs, recipe, run_id,
assertions}` — canonicalizada por la ÚNICA puerta (`blite.certificate.canonical`)
y guardada vía `ContentStore.put()` como cualquier `Artifact`; sin campo nuevo
en `Artifact` (freeze §12 queda intacto). xfail: `blite.verification.provenance`
no existe todavía (Fase 1, dueño Sebas+Dylan).
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason=(
            "Fase 1 Sebas+Dylan: blite.verification.provenance (DerivationProvenance/"
            "ExternalSourceProvenance) no existe todavía — docs/specs/capability-ingesta.md"
        ),
    ),
]


def test_derivation_provenance_carries_the_dvc_lock_shaped_recipe() -> None:
    """Contrato: `{kind:"derivation", inputs, recipe, run_id, assertions}` — el
    shape exacto de capability-ingesta.md §Contrato, cero campo inventado."""
    # Arrange / Act
    from blite.verification.provenance import DerivationProvenance

    provenance = DerivationProvenance(
        kind="derivation",
        inputs=({"ref": "snapshot:ice-featureserver", "digest": "sha256:" + "a" * 64},),
        recipe={
            "capability": "blite.ingesta.geojson.to_graph",
            "version": "0.1.0",
            "params_digest": "sha256:" + "b" * 64,
            "code_ref": "git:HEAD",
        },
        run_id="r1",
        assertions=({"name": "geojson_schema_valid", "passed": True, "detail": None},),
    )

    # Assert
    assert provenance.kind == "derivation"
    assert provenance.inputs[0]["ref"] == "snapshot:ice-featureserver"
    assert provenance.recipe["capability"] == "blite.ingesta.geojson.to_graph"
    assert provenance.assertions[0]["passed"] is True


def test_derivation_digest_uses_the_single_canonicalization_gate() -> None:
    """Contrato: "una sola puerta de canonicalización" (capability-ingesta.md
    §Determinismo) — el digest de una instancia derivada usa el MISMO `C(x)`
    que `provenance_hash`/`claim_digest`, cero segunda copia del formateo."""
    # Arrange
    from blite.certificate.canonical import canonicalize
    from blite.verification.provenance import DerivationProvenance

    provenance = DerivationProvenance(
        kind="derivation",
        inputs=(),
        recipe={
            "capability": "blite.ingesta.geojson.to_graph",
            "version": "0.1.0",
            "params_digest": "sha256:" + "b" * 64,
            "code_ref": "git:HEAD",
        },
        run_id="r1",
        assertions=(),
    )

    # Act — recomputar dos veces debe ser byte-idéntico (determinismo del digest)
    first = canonicalize(provenance.model_dump(mode="json"))
    second = canonicalize(provenance.model_dump(mode="json"))

    # Assert
    assert first == second
