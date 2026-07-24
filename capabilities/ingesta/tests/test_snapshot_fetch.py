"""Unit tests de `blite.ingesta.snapshot.fetch` (`SnapshotFetch`).

ADR-008: este archivo de test SÍ puede importar `blite.*` (solo la fuente
`blite_cap_ingesta` no puede) — usa el `InMemoryContentStore` real del
engine como `ContentSink` concreto para probar la integración end-to-end.
"""

from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime

import pytest

from blite.runtime.content_store import InMemoryContentStore
from blite_cap_ingesta import SnapshotFetch

_SNAPSHOT_BYTES = b'{"type":"FeatureCollection","features":[]}'


def _base_inputs(**overrides: object) -> dict[str, object]:
    inputs: dict[str, object] = {
        "content_base64": base64.b64encode(_SNAPSHOT_BYTES).decode("ascii"),
        "media_type": "application/geo+json",
        "source_uri": "https://example.test/FeatureServer/0/query",
        "retrieved_at": datetime(2026, 7, 24, tzinfo=UTC),
        "domain_id": "d-default",
        "content_store": InMemoryContentStore(),
        "http_status": 200,
    }
    inputs.update(overrides)
    return inputs


class TestManifest:
    def test_manifest_id_matches_the_registered_entry_point(self) -> None:
        assert SnapshotFetch().manifest.id == "blite.ingesta.snapshot.fetch"

    def test_manifest_schemas_avoid_scenario_terms(self) -> None:
        """ADR-029: cero 'islanding'/'ICE'/'subestación' en id/description/schema."""
        # Arrange
        manifest = SnapshotFetch().manifest
        blob = " ".join(
            [
                manifest.id,
                manifest.description,
                str(manifest.input_schema),
                str(manifest.output_schema),
            ]
        ).lower()

        # Assert
        for forbidden in ("islanding", "subestacion", "subestación", " ice "):
            assert forbidden not in blob


class TestFetchSnapshotHappyPath:
    def test_returns_artifact_with_sha256_of_exact_bytes(self) -> None:
        # Arrange
        inputs = _base_inputs()

        # Act
        result = SnapshotFetch().invoke(inputs)

        # Assert — spec §Contrato punto 1: el digest ES sha256 sobre los bytes EXACTOS
        assert (
            result["artifact"]["digest"] == hashlib.sha256(_SNAPSHOT_BYTES).hexdigest()
        )
        assert result["artifact"]["size_bytes"] == len(_SNAPSHOT_BYTES)
        assert result["artifact"]["domain_id"] == "d-default"

    def test_returns_external_source_shaped_provenance(self) -> None:
        # Arrange
        inputs = _base_inputs()

        # Act
        result = SnapshotFetch().invoke(inputs)

        # Assert
        provenance = result["provenance"]
        assert provenance["kind"] == "external-source"
        assert provenance["uri"] == "https://example.test/FeatureServer/0/query"
        assert provenance["http_status"] == 200
        assert provenance["content_type"] == "application/geo+json"

    def test_reput_of_identical_bytes_is_idempotent(self) -> None:
        """O3 (freeze §12): el contenido define su identidad — re-put del
        MISMO snapshot da el MISMO digest, no un duplicado."""
        # Arrange
        store = InMemoryContentStore()
        inputs = _base_inputs(content_store=store)

        # Act
        first = SnapshotFetch().invoke(inputs)
        second = SnapshotFetch().invoke(inputs)

        # Assert
        assert first["artifact"]["digest"] == second["artifact"]["digest"]

    def test_two_fetches_of_different_bytes_get_different_digests(self) -> None:
        """El ancla es el snapshot, jamás la uri — misma uri, bytes
        distintos (fetch en otro instante) ⇒ digest distinto (spec §Contrato)."""
        # Arrange
        store = InMemoryContentStore()
        first_inputs = _base_inputs(content_store=store)
        second_inputs = _base_inputs(
            content_store=store,
            content_base64=base64.b64encode(_SNAPSHOT_BYTES + b" ").decode("ascii"),
        )

        # Act
        first = SnapshotFetch().invoke(first_inputs)
        second = SnapshotFetch().invoke(second_inputs)

        # Assert
        assert first["artifact"]["digest"] != second["artifact"]["digest"]
        assert first["provenance"]["uri"] == second["provenance"]["uri"]


class TestFetchSnapshotFailFast:
    def test_missing_required_key_raises_value_error(self) -> None:
        # Arrange
        inputs = _base_inputs()
        del inputs["source_uri"]

        # Act / Assert
        with pytest.raises(ValueError, match="source_uri"):
            SnapshotFetch().invoke(inputs)

    def test_missing_content_store_raises_type_error(self) -> None:
        # Arrange
        inputs = _base_inputs()
        del inputs["content_store"]

        # Act / Assert
        with pytest.raises(TypeError, match="content_store"):
            SnapshotFetch().invoke(inputs)

    def test_content_store_not_shaped_like_a_content_sink_raises_type_error(
        self,
    ) -> None:
        # Arrange
        inputs = _base_inputs(content_store=object())

        # Act / Assert
        with pytest.raises(TypeError, match="ContentSink"):
            SnapshotFetch().invoke(inputs)
