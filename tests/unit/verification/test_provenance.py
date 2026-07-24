"""Unit tests de `blite.verification.provenance` — docs/specs/capability-ingesta.md.

Cubre: forma exacta del contrato (`tests/seeds/test_seed_ingesta_receta.py`
fija el caso feliz), inmutabilidad/`extra=forbid`, la validación de forma
(`TypedDict` de `recipe`/`inputs`/`assertions`) que rechaza recetas/inputs/
assertions incompletos, `parse_provenance` (despacho por `kind`) y determinismo
del digest bajo la única puerta (`blite.certificate.canonical.canonicalize`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from blite.certificate.canonical import canonicalize
from blite.verification.provenance import (
    DerivationProvenance,
    DerivationRecipe,
    ExternalSourceProvenance,
    parse_provenance,
)

_VALID_RECIPE: DerivationRecipe = {
    "capability": "blite.ingesta.geojson.to_graph",
    "version": "0.1.0",
    "params_digest": "sha256:" + "b" * 64,
    "code_ref": "git:HEAD",
}


class TestExternalSourceProvenanceShape:
    def test_carries_uri_and_retrieval_metadata(self) -> None:
        # Arrange / Act
        provenance = ExternalSourceProvenance(
            uri="https://example.test/FeatureServer/0/query",
            retrieved_at=datetime(2026, 7, 24, tzinfo=UTC),
            content_type="application/geo+json",
            http_status=200,
        )

        # Assert
        assert provenance.kind == "external-source"
        assert provenance.content_type == "application/geo+json"
        assert provenance.http_status == 200

    def test_is_frozen(self) -> None:
        # Arrange
        provenance = ExternalSourceProvenance(
            uri="https://example.test", retrieved_at=datetime(2026, 7, 24, tzinfo=UTC)
        )

        # Act / Assert
        with pytest.raises(ValidationError):
            provenance.uri = "https://mutated.test"

    def test_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            ExternalSourceProvenance(
                uri="https://example.test",
                retrieved_at=datetime(2026, 7, 24, tzinfo=UTC),
                unexpected_field="nope",  # type: ignore[call-arg]
            )


class TestDerivationProvenanceValidation:
    def test_rejects_recipe_missing_required_keys(self) -> None:
        # Arrange — recipe sin 'code_ref', deliberadamente malformada: tipo Any
        # para probar el rechazo en RUNTIME (la validación de forma), no en el
        # type-checker (que ya sabría que le falta la llave).
        bad_recipe: Any = {
            "capability": "blite.ingesta.geojson.to_graph",
            "version": "0.1.0",
            "params_digest": "sha256:" + "b" * 64,
        }

        # Act / Assert
        with pytest.raises(ValidationError, match="code_ref"):
            DerivationProvenance(
                inputs=(), recipe=bad_recipe, run_id="r1", assertions=()
            )

    def test_rejects_input_entry_missing_digest(self) -> None:
        # input sin 'digest' — malformado a propósito (Any → rechazo en runtime)
        bad_inputs: Any = ({"ref": "snapshot:x"},)
        with pytest.raises(ValidationError, match="digest"):
            DerivationProvenance(
                inputs=bad_inputs, recipe=_VALID_RECIPE, run_id="r1", assertions=()
            )

    def test_rejects_assertion_entry_missing_passed(self) -> None:
        # assertion sin 'passed' — malformada a propósito (Any → rechazo en runtime)
        bad_assertions: Any = ({"name": "geojson_schema_valid"},)
        with pytest.raises(ValidationError, match="passed"):
            DerivationProvenance(
                inputs=(),
                recipe=_VALID_RECIPE,
                run_id="r1",
                assertions=bad_assertions,
            )

    def test_assertions_stay_dict_subscriptable_not_nested_models(self) -> None:
        """Contrato del seed: `assertions[0]["passed"]` debe funcionar — un
        sub-modelo Pydantic anidado no sería subscriptable."""
        # Arrange
        provenance = DerivationProvenance(
            inputs=(),
            recipe=_VALID_RECIPE,
            run_id="r1",
            assertions=(
                {"name": "geojson_schema_valid", "passed": True, "detail": None},
            ),
        )

        # Act / Assert
        assert provenance.assertions[0]["name"] == "geojson_schema_valid"


class TestParseProvenance:
    def test_dispatches_external_source_by_kind(self) -> None:
        # Arrange
        data = {
            "kind": "external-source",
            "uri": "https://example.test",
            "retrieved_at": "2026-07-24T00:00:00Z",
        }

        # Act
        parsed = parse_provenance(data)

        # Assert
        assert isinstance(parsed, ExternalSourceProvenance)

    def test_dispatches_derivation_by_kind(self) -> None:
        # Arrange
        data: dict[str, Any] = {
            "kind": "derivation",
            "inputs": [],
            "recipe": _VALID_RECIPE,
            "run_id": "r1",
            "assertions": [],
        }

        # Act
        parsed = parse_provenance(data)

        # Assert
        assert isinstance(parsed, DerivationProvenance)

    def test_rejects_unknown_kind(self) -> None:
        with pytest.raises(ValidationError):
            parse_provenance({"kind": "not-a-real-kind"})


class TestSingleCanonicalizationGateDeterminism:
    """Spec §Determinismo: 'una sola puerta de canonicalización' — recomputar
    el digest dos veces (incluso con distinto orden de inserción de llaves
    en `recipe`) debe ser byte-idéntico."""

    def test_key_insertion_order_does_not_affect_the_digest(self) -> None:
        # Arrange — mismas llaves, orden de inserción distinto
        recipe_a: DerivationRecipe = {
            "capability": "blite.ingesta.geojson.to_graph",
            "version": "0.1.0",
            "params_digest": "sha256:" + "b" * 64,
            "code_ref": "git:HEAD",
        }
        recipe_b: DerivationRecipe = {
            "code_ref": "git:HEAD",
            "params_digest": "sha256:" + "b" * 64,
            "version": "0.1.0",
            "capability": "blite.ingesta.geojson.to_graph",
        }
        provenance_a = DerivationProvenance(
            inputs=(), recipe=recipe_a, run_id="r1", assertions=()
        )
        provenance_b = DerivationProvenance(
            inputs=(), recipe=recipe_b, run_id="r1", assertions=()
        )

        # Act
        bytes_a = canonicalize(provenance_a.model_dump(mode="json"))
        bytes_b = canonicalize(provenance_b.model_dump(mode="json"))

        # Assert
        assert bytes_a == bytes_b

    def test_external_source_provenance_canonicalizes_deterministically(
        self,
    ) -> None:
        # Arrange
        provenance = ExternalSourceProvenance(
            uri="https://example.test/FeatureServer/0/query",
            retrieved_at=datetime(2026, 7, 24, tzinfo=UTC),
            content_type="application/geo+json",
            http_status=200,
        )

        # Act
        first = canonicalize(provenance.model_dump(mode="json"))
        second = canonicalize(provenance.model_dump(mode="json"))

        # Assert
        assert first == second
