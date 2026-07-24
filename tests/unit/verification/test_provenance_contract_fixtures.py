"""Fixtures de contrato de la costura B↔A (ingesta) — docs/specs/README.md
§Fixtures de costura: "el fixture ES el contrato" + "un test anti-drift
asegura que canónico y espejo son byte-idénticos". Origen único:
`scripts/gen-fixtures-ingesta.py` (modelos Pydantic de
`blite.verification.provenance`) — este test SOLO lee lo ya escrito, jamás
inventa el dato.
"""

from __future__ import annotations

import json
from pathlib import Path

from blite.verification.provenance import (
    DerivationProvenance,
    ExternalSourceProvenance,
    parse_provenance,
)

_REPO = Path(__file__).resolve().parents[3]
_CANONICAL_DIR = _REPO / "tests" / "fixtures" / "contract" / "ingesta"
_MIRROR_DIR = _REPO / "apps" / "studio" / "src" / "fixtures" / "contract" / "ingesta"


class TestFixturesMirrorTheCanonicalSource:
    def test_snapshot_example_is_byte_identical_in_both_locations(self) -> None:
        # Arrange / Act
        canonical = (_CANONICAL_DIR / "snapshot-example.json").read_bytes()
        mirror = (_MIRROR_DIR / "snapshot-example.json").read_bytes()

        # Assert
        assert canonical == mirror

    def test_derivation_example_is_byte_identical_in_both_locations(self) -> None:
        # Arrange / Act
        canonical = (_CANONICAL_DIR / "derivation-example.json").read_bytes()
        mirror = (_MIRROR_DIR / "derivation-example.json").read_bytes()

        # Assert
        assert canonical == mirror


class TestFixturesParseAgainstTheContractModels:
    def test_snapshot_example_parses_as_external_source_provenance(self) -> None:
        # Arrange
        data = json.loads((_CANONICAL_DIR / "snapshot-example.json").read_text())

        # Act
        parsed = parse_provenance(data)

        # Assert
        assert isinstance(parsed, ExternalSourceProvenance)

    def test_derivation_example_parses_as_derivation_provenance(self) -> None:
        # Arrange
        data = json.loads((_CANONICAL_DIR / "derivation-example.json").read_text())

        # Act
        parsed = parse_provenance(data)

        # Assert
        assert isinstance(parsed, DerivationProvenance)
        assert parsed.recipe["capability"] == "blite.ingesta.geojson.to_graph"
