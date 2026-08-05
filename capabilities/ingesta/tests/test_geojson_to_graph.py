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


def _connected_component_sizes(aristas: list[list[Any]]) -> list[int]:
    """BFS mínimo, sin dependencias externas — evita acoplar los tests de
    esta capability a `networkx` (no es dependencia de `blite_cap_ingesta`)."""
    adjacency: dict[int, set[int]] = {}
    for i, j, _weight in aristas:
        adjacency.setdefault(i, set()).add(j)
        adjacency.setdefault(j, set()).add(i)

    seen: set[int] = set()
    sizes: list[int] = []
    for start in adjacency:
        if start in seen:
            continue
        stack: list[int] = [start]
        component: set[int] = set()
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            stack.extend(adjacency[node] - component)
        seen |= component
        sizes.append(len(component))
    return sizes


def _point(fid: int, name: str) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
        "properties": {"FID": fid, "Name": name},
    }


def _named_edge(fid: int, endpoint: str, magnitude: int) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
        "properties": {"FID": fid, "Endpoint": endpoint, "Magnitude": magnitude},
    }


def _invoke_endpoint_name_match(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]], **overrides: object
) -> dict[str, Any]:
    nodes_fc = {"type": "FeatureCollection", "features": nodes}
    edges_fc = {"type": "FeatureCollection", "features": edges}
    inputs = _base_inputs(
        nodes_content_base64=_fc_b64(nodes_fc),
        edges_content_base64=_fc_b64(edges_fc),
        edge_strategy="endpoint-name-match",
        node_match_property="Name",
        endpoint_property="Endpoint",
        endpoint_separator="-",
    )
    inputs.update(overrides)
    return GeojsonToGraph().invoke(inputs)


class TestEndpointNameMatchStrategyGenericBehaviour:
    """Estrategia genérica nueva `edge_strategy="endpoint-name-match"`
    (ADR-029: los NOMBRES de propiedad concretos — aquí sintéticos, en
    `scripts/gen_corpus_ice.py` "Circuito"/"Subestacio"/"Voltaje" — viajan
    como PARAMS de invocación, jamás en el manifest; ver
    `TestManifest.test_manifest_schemas_avoid_scenario_terms`)."""

    def test_parses_a_dash_b_and_connects_two_matched_nodes(self) -> None:
        # Arrange
        nodes = [_point(1, "Alpha"), _point(2, "Beta")]
        edges = [_named_edge(1, "Alpha-Beta", 100)]

        # Act
        result = _invoke_endpoint_name_match(nodes, edges)

        # Assert
        assert result["graph"]["n_nodos"] == 2
        assert result["graph"]["aristas"] == [[0, 1, 1]]

    def test_falls_back_to_definite_article_prefixed_node_name(self) -> None:
        # Arrange — "Colima" (crudo, sin artículo) debe matchear un nodo
        # nombrado "La Colima" (mismo fallback que el espejo ICE).
        nodes = [_point(1, "La Colima"), _point(2, "Ribera")]
        edges = [_named_edge(1, "Colima-Ribera", 100)]

        # Act
        result = _invoke_endpoint_name_match(nodes, edges)

        # Assert
        assert result["graph"]["n_nodos"] == 2
        assert result["graph"]["aristas"] == [[0, 1, 1]]

    def test_strips_trailing_circuit_digits_before_matching(self) -> None:
        # Arrange — "Beta2" debe normalizar a "beta" (sufijo de circuito
        # paralelo, no parte del nombre).
        nodes = [_point(1, "Alpha"), _point(2, "Beta")]
        edges = [_named_edge(1, "Alpha-Beta2", 100)]

        # Act
        result = _invoke_endpoint_name_match(nodes, edges)

        # Assert
        assert result["graph"]["aristas"] == [[0, 1, 1]]

    def test_discards_edge_with_unknown_endpoint_and_reports_it_honestly(
        self,
    ) -> None:
        # Arrange
        nodes = [_point(1, "Alpha"), _point(2, "Beta")]
        edges = [
            _named_edge(1, "Alpha-Beta", 100),
            _named_edge(2, "Alpha-Unknown", 100),
        ]

        # Act
        result = _invoke_endpoint_name_match(nodes, edges)

        # Assert
        assert result["graph"]["aristas"] == [[0, 1, 1]]
        assertions = {a["name"]: a for a in result["provenance"]["assertions"]}
        assert assertions["edge_endpoint_names_resolved"]["passed"] is False
        assert (
            assertions["edge_endpoint_names_resolved"]["detail"]["discarded_count"] == 1
        )

    def test_discards_edge_resolving_to_the_same_node_on_both_sides(self) -> None:
        # Arrange — "Alpha-Alpha2" normaliza ambos lados al mismo nodo.
        nodes = [_point(1, "Alpha")]
        edges = [_named_edge(1, "Alpha-Alpha2", 100)]

        # Act
        result = _invoke_endpoint_name_match(nodes, edges)

        # Assert
        assert result["graph"]["n_nodos"] == 0
        assert result["graph"]["aristas"] == []

    def test_isolated_node_with_no_resolved_edge_is_excluded_from_output(
        self,
    ) -> None:
        # Arrange — "Gamma" nunca aparece en ningún endpoint parseable.
        nodes = [_point(1, "Alpha"), _point(2, "Beta"), _point(3, "Gamma")]
        edges = [_named_edge(1, "Alpha-Beta", 100)]

        # Act
        result = _invoke_endpoint_name_match(nodes, edges)

        # Assert
        assert result["graph"]["n_nodos"] == 2
        names = {n["properties"]["Name"] for n in result["graph"]["nodos"].values()}
        assert names == {"Alpha", "Beta"}

    def test_aggregates_parallel_circuits_counting_by_default(self) -> None:
        # Arrange — dos líneas paralelas Alpha<->Beta (sufijos de circuito).
        nodes = [_point(1, "Alpha"), _point(2, "Beta")]
        edges = [
            _named_edge(1, "Alpha-Beta1", 100),
            _named_edge(2, "Alpha-Beta2", 230),
        ]

        # Act
        result = _invoke_endpoint_name_match(nodes, edges, weight_property=None)

        # Assert
        assert result["graph"]["aristas"] == [[0, 1, 2]]

    def test_weight_property_sums_magnitude_across_parallel_circuits(self) -> None:
        # Arrange
        nodes = [_point(1, "Alpha"), _point(2, "Beta")]
        edges = [
            _named_edge(1, "Alpha-Beta1", 100),
            _named_edge(2, "Alpha-Beta2", 230),
        ]

        # Act
        result = _invoke_endpoint_name_match(nodes, edges, weight_property="Magnitude")

        # Assert
        assert result["graph"]["aristas"] == [[0, 1, 330]]

    def test_missing_strategy_specific_keys_raises_value_error(self) -> None:
        # Arrange
        inputs = _base_inputs(edge_strategy="endpoint-name-match")

        # Act / Assert
        with pytest.raises(ValueError, match="endpoint-name-match"):
            GeojsonToGraph().invoke(inputs)

    def test_unknown_edge_strategy_raises_value_error(self) -> None:
        # Arrange
        inputs = _base_inputs(edge_strategy="not-a-real-strategy")

        # Act / Assert
        with pytest.raises(ValueError, match="not-a-real-strategy"):
            GeojsonToGraph().invoke(inputs)

    def test_shape_invalid_input_reports_skipped_assertion_not_a_crash(self) -> None:
        # Arrange
        broken_nodes = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": "not-a-coordinate"},
                    "properties": {"FID": 1, "Name": "Alpha"},
                }
            ],
        }
        inputs = _base_inputs(
            nodes_content_base64=_fc_b64(broken_nodes),
            edge_strategy="endpoint-name-match",
            node_match_property="Name",
            endpoint_property="Endpoint",
        )

        # Act
        result = GeojsonToGraph().invoke(inputs)

        # Assert
        assertions = {a["name"]: a for a in result["provenance"]["assertions"]}
        assert assertions["edge_endpoint_names_resolved"]["passed"] is False
        assert result["graph"]["n_nodos"] == 0


class TestEndpointNameMatchDerivesTheRealIce68Network:
    """Paridad con `reto1-vanilla/scripts/build_cr_instances.py`
    (`load_national_graph`): la red ICE real vía `Circuito`/`Subestacio`
    produce 68 nodos / 90 aristas en UN único componente conexo — de las 70
    subestaciones del snapshot, 2 nunca resuelven ningún `Circuito` (quedan
    fuera de la salida) y 8 líneas se descartan por endpoint desconocido."""

    @staticmethod
    def _invoke() -> dict[str, Any]:
        inputs = _base_inputs(
            edge_strategy="endpoint-name-match",
            node_match_property="Subestacio",
            endpoint_property="Circuito",
            endpoint_separator="-",
        )
        return GeojsonToGraph().invoke(inputs)

    def test_produces_68_nodes_and_90_edges(self) -> None:
        # Act
        result = self._invoke()

        # Assert
        assert result["graph"]["n_nodos"] == 68
        assert len(result["graph"]["aristas"]) == 90

    def test_forms_a_single_connected_component(self) -> None:
        # Act
        result = self._invoke()

        # Assert
        sizes = _connected_component_sizes(result["graph"]["aristas"])
        assert sizes == [68]

    def test_reports_eight_discarded_lines_by_unknown_endpoint(self) -> None:
        # Act
        result = self._invoke()

        # Assert
        assertions = {a["name"]: a for a in result["provenance"]["assertions"]}
        assert assertions["edge_endpoint_names_resolved"]["passed"] is False
        assert (
            assertions["edge_endpoint_names_resolved"]["detail"]["discarded_count"] == 8
        )

    def test_edges_are_sorted_with_i_less_than_j(self) -> None:
        # Act
        result = self._invoke()

        # Assert
        aristas = result["graph"]["aristas"]
        for i, j, _weight in aristas:
            assert i < j
        pairs = [(i, j) for i, j, _weight in aristas]
        assert pairs == sorted(pairs)

    def test_output_canonicalizes_deterministically(self) -> None:
        # Act
        first = canonicalize(self._invoke()["graph"])
        second = canonicalize(self._invoke()["graph"])

        # Assert
        assert first == second


class TestBranchIdsConvencionHibrida:
    """C-8 (`docs/specs/superficie-visual.md` §8): la salida estampa un id por
    rama, 1:1 con `aristas`. Dos mitades — la canónica `L{min}-{max}[-k]`
    (modelos sin GIS) y el `edge_id_property` del portal (instancias derivadas
    de GIS, donde el dato del cliente conserva SU identidad)."""

    def test_por_defecto_los_ids_son_canonicos_y_alineados_1a1(self) -> None:
        # Arrange
        nodes = [_point(1, "A"), _point(2, "B"), _point(3, "C")]
        edges = [
            _named_edge(10, "A-B", 138),
            _named_edge(11, "B-C", 230),
        ]

        # Act
        result = _invoke_endpoint_name_match(nodes, edges)

        # Assert
        graph = result["graph"]
        assert graph["branch_id_convention"] == "canonical-l-min-max@v1"
        assert len(graph["branch_ids"]) == len(graph["aristas"])
        assert graph["branch_ids"] == ["L0-1", "L1-2"]

    def test_edge_id_property_conserva_la_identidad_del_portal(self) -> None:
        """Estrategia 1:1 (`nearest-neighbor`): el FID del portal ES el id."""
        # Arrange
        nodes_fc = {
            "type": "FeatureCollection",
            "features": [_point(1, "A"), _point(2, "B")],
        }
        edges_fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[0.0, 0.0], [0.0, 0.0]],
                    },
                    "properties": {"FID": 70143, "OBJECTID": 991},
                }
            ],
        }
        inputs = _base_inputs(
            nodes_content_base64=_fc_b64(nodes_fc),
            edges_content_base64=_fc_b64(edges_fc),
            edge_id_property="OBJECTID",
        )

        # Act
        graph = GeojsonToGraph().invoke(inputs)["graph"]

        # Assert
        assert graph["branch_id_convention"] == "edge-id-property@v1"
        assert graph["branch_ids"] == ["991"]

    def test_edge_id_property_con_estrategia_que_agrega_falla_fuerte(self) -> None:
        """La agregación de paralelas destruye el 1:1 feature↔rama: un id de
        portal por rama agregada sería una mentira. Se rechaza en frontera en
        vez de elegir en silencio uno de los N features."""
        # Arrange
        nodes = [_point(1, "A"), _point(2, "B")]
        edges = [_named_edge(10, "A-B", 138), _named_edge(11, "A-B", 230)]

        # Act / Assert
        with pytest.raises(ValueError, match="edge_id_property"):
            _invoke_endpoint_name_match(nodes, edges, edge_id_property="FID")

    def test_paralelas_canonicas_llevan_sufijo_en_estrategia_1a1(self) -> None:
        # Arrange
        nodes_fc = {
            "type": "FeatureCollection",
            "features": [_point(1, "A"), _point(2, "B")],
        }
        line = {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [0.0, 0.0]]},
            "properties": {"FID": 1},
        }
        edges_fc = {
            "type": "FeatureCollection",
            "features": [line, {**line, "properties": {"FID": 2}}],
        }
        inputs = _base_inputs(
            nodes_content_base64=_fc_b64(nodes_fc),
            edges_content_base64=_fc_b64(edges_fc),
        )

        # Act
        graph = GeojsonToGraph().invoke(inputs)["graph"]

        # Assert — mismo par de nodos dos veces ⇒ ambas reciben sufijo
        assert graph["branch_ids"] == ["L0-0-1", "L0-0-2"]

    def test_forma_invalida_no_inventa_ids(self) -> None:
        """Sin derivación no hay ramas — `branch_ids` vacío, jamás un id
        fabricado sobre índices que no se computaron."""
        # Arrange
        nodes = [_point(1, "A"), _point(1, "B")]  # FID duplicado ⇒ tabular inválido
        edges = [_named_edge(10, "A-B", 138)]

        # Act
        graph = _invoke_endpoint_name_match(nodes, edges)["graph"]

        # Assert
        assert graph["aristas"] == []
        assert graph["branch_ids"] == []

    def test_la_red_real_estampa_un_id_por_rama(self) -> None:
        # Arrange
        inputs = _base_inputs(
            edge_strategy="endpoint-name-match",
            node_match_property="Subestacio",
            endpoint_property="Circuito",
            endpoint_separator="-",
        )

        # Act
        graph = GeojsonToGraph().invoke(inputs)["graph"]

        # Assert
        assert len(graph["branch_ids"]) == len(graph["aristas"]) == 90
        assert len(set(graph["branch_ids"])) == 90
