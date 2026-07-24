"""Anti-drift: los fixtures de contrato del informe (C3b —
docs/specs/informe-derivado.md §"Tests de contrato", docs/specs/README.md
§"Fixtures de costura — un solo origen") tienen UN origen
(`scripts/gen-informe-fixtures.py`) y DOS espejos —
`tests/fixtures/contract/informe/` (canónico) y
`apps/studio/src/fixtures/contract/informe/` (lo que Vite puede importar).
Este test asegura que (a) ambos espejos son byte-idénticos, (b) el fixture
ES el contrato — parsea con el modelo Pydantic real, nadie inventa el dato —
y (c) `provenance.recipe.capability` es la capability esperada."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from blite.verification.provenance import DerivationProvenance

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "contract" / "informe"
STUDIO_FIXTURE_DIR = (
    REPO_ROOT / "apps" / "studio" / "src" / "fixtures" / "contract" / "informe"
)

_CASES = (
    ("figura-example.json", "blite.report.render_figure"),
    ("pdf-example.json", "blite.report.compile_pdf"),
)


def _load_canonical(filename: str) -> dict[str, Any]:
    return json.loads((TESTS_FIXTURE_DIR / filename).read_text("utf-8"))


class TestMirrorsAreByteIdentical:
    @pytest.mark.parametrize("filename,_capability", _CASES)
    def test_tests_fixture_matches_studio_fixture_byte_for_byte(
        self, filename: str, _capability: str
    ) -> None:
        # Arrange
        canonical = (TESTS_FIXTURE_DIR / filename).read_bytes()
        mirror = (STUDIO_FIXTURE_DIR / filename).read_bytes()

        # Assert
        assert canonical == mirror


class TestFixtureIsTheContract:
    @pytest.mark.parametrize("filename,_capability", _CASES)
    def test_fixture_parses_with_the_pydantic_derivation_provenance_model(
        self, filename: str, _capability: str
    ) -> None:
        # Arrange
        fixture = _load_canonical(filename)

        # Act — the fixture IS the contract: parse it with the real model,
        # never a hand-rolled shape assumption.
        provenance = DerivationProvenance(**fixture["provenance"])

        # Assert
        assert provenance.kind == "derivation"
        assert isinstance(fixture["digest"], str) and fixture["digest"]

    @pytest.mark.parametrize("filename,capability", _CASES)
    def test_recipe_capability_matches_the_expected_capability(
        self, filename: str, capability: str
    ) -> None:
        # Arrange
        fixture = _load_canonical(filename)
        provenance = DerivationProvenance(**fixture["provenance"])

        # Assert
        assert provenance.recipe["capability"] == capability


class TestPdfFixtureCarriesPageCount:
    def test_pdf_example_carries_a_page_count_within_the_eight_page_budget(
        self,
    ) -> None:
        # Arrange
        fixture = _load_canonical("pdf-example.json")

        # Assert
        assert isinstance(fixture["page_count"], int)
        assert 1 <= fixture["page_count"] <= 8
