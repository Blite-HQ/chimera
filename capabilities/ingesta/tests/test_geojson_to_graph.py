"""Unit tests de `blite.ingesta.geojson.to_graph` (`GeojsonToGraph`).

Incluye la derivación REAL de la red ICE-70 desde el espejo del GeoJSON
(`tests/fixtures/*.geojson`, copiado byte-a-byte de
`reto1-vanilla/data/raw/` — solo-lectura, ver `capabilities/ingesta/README.md`).

ADR-008: este archivo de test SÍ puede importar `blite.*` (solo la fuente
`blite_cap_ingesta` no puede) — usa `canonicalize()` para probar que la
salida de la capability es "lista para canonicalizar" (spec §Determinismo).
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest

from blite.certificate.canonical import canonicalize
from blite_cap_ingesta import GeojsonToGraph

_FIXTURES = Path(__file__).parent / "fixtures"
_NODES_PATH = _FIXTURES / "ice-subestaciones.geojson"
_EDGES_PATH = _FIXTURES / "ice-lineas-transmision.geojson"

_ICE_NODE_COUNT = 70
_ICE_EDGE_COUNT = (
    102  # una arista por feature de línea — spec: "aristas = líneas de transmisión"
)


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _base_inputs(**overrides: object) -> dict[str, Any]:
    inputs: dict[str, Any] = {
        "nodes_content_base64": _b64(_NODES_PATH),
        "edges_content_base64": _b64(_EDGES_PATH),
        "run_id": "r1",
        "params_digest": "sha256:" + "a" * 64,
        "code_ref": "git:HEAD",
        "inputs": [
            {"ref": "snapshot:ice-featureserver", "digest": "sha256:" + "b" * 64}
        ],
    }
    inputs.update(overrides)
    return inputs


def _fc_b64(feature_collection: dict[str, Any]) -> str:
    return base64.b64encode(json.dumps(feature_collection).encode("utf-8")).decode(
        "ascii"
    )


class TestManifest:
    def test_manifest_id_matches_the_registered_entry_point(self) -> None:
        assert GeojsonToGraph().manifest.id == "blite.ingesta.geojson.to_graph"

    def test_manifest_schemas_avoid_scenario_terms(self) -> None:
        """ADR-029: cero 'islanding'/'ICE'/'subestación' en id/description/schema."""
        # Arrange
        manifest = GeojsonToGraph().manifest
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


class TestDerivesTheRealIce70Network:
    def test_produces_70_nodes(self) -> None:
        # Arrange
        inputs = _base_inputs()

        # Act
        result = GeojsonToGraph().invoke(inputs)

        # Assert
        assert result["graph"]["n_nodos"] == _ICE_NODE_COUNT
        assert len(result["graph"]["nodos"]) == _ICE_NODE_COUNT

    def test_produces_one_edge_per_transmission_line_feature(self) -> None:
        # Arrange
        inputs = _base_inputs()

        # Act
        result = GeojsonToGraph().invoke(inputs)

        # Assert
        assert len(result["graph"]["aristas"]) == _ICE_EDGE_COUNT

    def test_edge_endpoints_reference_valid_node_indices(self) -> None:
        # Arrange
        inputs = _base_inputs()

        # Act
        result = GeojsonToGraph().invoke(inputs)

        # Assert
        n = result["graph"]["n_nodos"]
        for i, j, _weight in result["graph"]["aristas"]:
            assert 0 <= i < n
            assert 0 <= j < n

    def test_node_zero_is_the_lowest_fid_feature(self) -> None:
        """Determinismo punto 1: features ordenadas por ID estable (FID)
        antes de construir `nodos` — FID=1 (Pailas) debe caer en el índice 0."""
        # Arrange
        inputs = _base_inputs()

        # Act
        result = GeojsonToGraph().invoke(inputs)

        # Assert
        assert result["graph"]["nodos"]["0"]["source_ref"] == 1
        assert result["graph"]["nodos"]["0"]["properties"]["Subestacio"] == "Pailas"

    def test_geometry_and_tabular_assertions_pass_on_real_data(self) -> None:
        # Arrange
        inputs = _base_inputs()

        # Act
        result = GeojsonToGraph().invoke(inputs)

        # Assert
        assertions = {a["name"]: a for a in result["provenance"]["assertions"]}
        assert assertions["node_geojson_schema_valid"]["passed"] is True
        assert assertions["edge_geojson_schema_valid"]["passed"] is True
        assert assertions["tabular_schema_valid"]["passed"] is True

    def test_honestly_reports_self_loop_and_far_endpoint_edges(self) -> None:
        """El derivador NUNCA descarta una línea silenciosamente — la red
        ICE real trae líneas fronterizas/spurs cuyos extremos no resuelven a
        dos nodos distintos ni dentro de la tolerancia de snap; eso se
        reporta como assertion en `passed=False`, no se oculta."""
        # Arrange
        inputs = _base_inputs()

        # Act
        result = GeojsonToGraph().invoke(inputs)

        # Assert
        assertions = {a["name"]: a for a in result["provenance"]["assertions"]}
        assert assertions["no_self_loop_edges"]["passed"] is False
        assert assertions["no_self_loop_edges"]["detail"]["self_loop_count"] > 0
        assert assertions["edge_endpoints_within_tolerance"]["passed"] is False


class TestDeterminism:
    def test_repeated_invocations_produce_identical_output(self) -> None:
        # Arrange
        inputs = _base_inputs()

        # Act
        first = GeojsonToGraph().invoke(inputs)
        second = GeojsonToGraph().invoke(inputs)

        # Assert
        assert first == second

    def test_output_canonicalizes_to_identical_bytes_twice(self) -> None:
        """Spec §Determinismo punto 3: la salida queda 'lista para
        canonicalizar' — floats/orden intactos, cero segunda copia del
        formateo (el gate lo cruza el caller, esta capability nunca lo
        importa — ADR-008)."""
        # Arrange
        result = GeojsonToGraph().invoke(_base_inputs())

        # Act
        first = canonicalize(result["graph"])
        second = canonicalize(result["graph"])

        # Assert
        assert first == second


class TestValidationCatchesMalformedInput:
    def test_node_geometry_validation_fails_on_malformed_geometry(self) -> None:
        # Arrange
        broken_nodes = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": "not-a-coordinate"},
                    "properties": {"FID": 1},
                }
            ],
        }
        inputs = _base_inputs(nodes_content_base64=_fc_b64(broken_nodes))

        # Act
        result = GeojsonToGraph().invoke(inputs)

        # Assert
        assertions = {a["name"]: a for a in result["provenance"]["assertions"]}
        assert assertions["node_geojson_schema_valid"]["passed"] is False
        assert assertions["node_geojson_schema_valid"]["detail"]["errors"]

    def test_tabular_validation_fails_on_duplicate_node_ids(self) -> None:
        # Arrange
        duplicate_fid_nodes = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
                    "properties": {"FID": 1},
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [1.0, 1.0]},
                    "properties": {"FID": 1},
                },
            ],
        }
        empty_edges: dict[str, Any] = {"type": "FeatureCollection", "features": []}
        inputs = _base_inputs(
            nodes_content_base64=_fc_b64(duplicate_fid_nodes),
            edges_content_base64=_fc_b64(empty_edges),
        )

        # Act
        result = GeojsonToGraph().invoke(inputs)

        # Assert
        assertions = {a["name"]: a for a in result["provenance"]["assertions"]}
        assert assertions["tabular_schema_valid"]["passed"] is False

    def test_unsupported_edge_geometry_type_raises_value_error(self) -> None:
        # Arrange
        polygon_edges = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                    },
                    "properties": {"FID": 1},
                }
            ],
        }
        inputs = _base_inputs(edges_content_base64=_fc_b64(polygon_edges))

        # Act / Assert
        with pytest.raises(ValueError, match="Polygon"):
            GeojsonToGraph().invoke(inputs)


class TestFailFastOnMissingInputs:
    def test_missing_required_key_raises_value_error(self) -> None:
        # Arrange
        inputs = _base_inputs()
        del inputs["run_id"]

        # Act / Assert
        with pytest.raises(ValueError, match="run_id"):
            GeojsonToGraph().invoke(inputs)
