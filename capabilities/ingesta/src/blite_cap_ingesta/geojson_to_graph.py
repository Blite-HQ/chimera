"""Lógica pura de `blite.ingesta.geojson.to_graph` (docs/specs/capability-ingesta.md).

Deriva topología genérica `{aristas, n_nodos, nodos}` de un par de
`FeatureCollection` GeoJSON (nodos = features de punto; aristas = features
de línea), validando forma ANTES de declarar la instancia derivada válida:
`geojson-pydantic` (RFC 7946) para geometría, `pandera` para tabular. El
resultado — pase o falle — entra como `assertions` (mismo espíritu que
`dataQualityAssertions` de OpenLineage, R2).

Dos estrategias de derivación de aristas, seleccionadas por `edge_strategy`
(ADR-029: los NOMBRES de estrategia y de parámetro son genéricos; los
VALORES concretos de un dominio — p. ej. los nombres de campo de la red ICE,
"Circuito"/"Subestacio"/"Voltaje" — viajan como PARAMS de invocación, JAMÁS
en el manifest):

- `"nearest-neighbor"` (default, comportamiento preexistente) — snap
  geométrico del extremo de cada línea al nodo más cercano por distancia.
- `"endpoint-name-match"` — parsea un par de nombres delimitados de una
  propiedad de arista (`endpoint_property`, separador `endpoint_separator`)
  y matchea cada lado por nombre normalizado contra una propiedad de nodo
  (`node_match_property`); útil cuando la fuente ya nombra sus extremos en
  vez de (o además de) traer geometría snap-eable. Solo los nodos que
  resuelven al menos una arista terminan en la salida — un nodo del snapshot
  que ninguna arista referencia queda fuera de `nodos`, honestamente (no hay
  "nodo aislado con grado 0" implícito). Pesos: `weight_property=None` cuenta
  aristas paralelas agregadas (uso "uniforme"); con `weight_property` fijo,
  suma esa propiedad entre las paralelas (p. ej. sumar niveles de tensión).

Determinismo (spec §Determinismo):
1. Features ORDENADAS por `node_id_property` (default `FID`, un ID estable
   de GIS — genérico, NO específico de un dominio) antes de construir
   `nodos`/`aristas` — un FeatureServer paginado no garantiza orden de
   iteración estable entre corridas.
2. Coordenadas/propiedades pasan TAL CUAL desde `json.loads` hasta el dict
   de salida — CERO reformateo de floats. La validación de geometría corre
   sobre una instancia PARSEADA APARTE (`geojson-pydantic`) que se descarta
   tras el chequeo; nunca se usa como fuente de los valores de salida,
   precisamente para no arriesgar una segunda ruta de coerción de floats.
3. Esta función NUNCA importa `blite.certificate.canonical.canonicalize` —
   ADR-008 (capabilities nunca importan el engine). El dict que devuelve
   queda "listo para canonicalizar" (sin floats reformateados, orden
   estable) — la única puerta la cruza el CALLER (engine), no esta capability.

Este módulo tampoco filtra ni descarta ninguna línea: cada feature de arista
del input produce exactamente una entrada en `aristas` (mismo orden FID),
incluidos self-loops o extremos lejos de cualquier nodo — la honestidad
sobre esos casos vive en `assertions` (`no_self_loop_edges`,
`edge_endpoints_within_tolerance`), nunca en un descarte silencioso.
"""

from __future__ import annotations

# pandas no publica stubs propios (mismo criterio que pandapower en
# blite/verification/execution.py) — pandera[pandas] ya lo trae como
# dependencia obligatoria (pandera.pandas no importa sin él), así que no es
# un import "lazy" real: se silencia solo ese reporte, el resto sigue en modo
# strict.
# pyright: reportMissingTypeStubs=false
import base64
import json
import math
import unicodedata
from typing import Any

import pandas as pd
import pandera.pandas as pa
from geojson_pydantic import Feature, FeatureCollection
from geojson_pydantic.geometries import Geometry
from pandera.errors import SchemaError
from pydantic import ValidationError

_DEFAULT_NODE_ID_PROPERTY = "FID"

# Tolerancia de "snap" (grados lon/lat) para reportar si un extremo de línea
# cae razonablemente cerca de su nodo más cercano — SOLO un signal de
# calidad de dato (`edge_endpoints_within_tolerance`), jamás un filtro que
# descarte aristas.
_ENDPOINT_SNAP_TOLERANCE_DEG = 0.01

_EDGE_STRATEGY_NEAREST_NEIGHBOR = "nearest-neighbor"
_EDGE_STRATEGY_ENDPOINT_NAME_MATCH = "endpoint-name-match"
_DEFAULT_EDGE_STRATEGY = _EDGE_STRATEGY_NEAREST_NEIGHBOR
_DEFAULT_ENDPOINT_SEPARATOR = "-"
# Fallback genérico de `endpoint-name-match`: algunas fuentes nombran un
# extremo sin artículo mientras el dataset de nodos lo antepone (p. ej. un
# extremo "Colima" que matchea un nodo "La Colima") — no es vocabulario de
# ningún escenario, es una heurística de matching de nombres reutilizable
# entre datasets con ese mismo sesgo de nomenclatura.
_ENDPOINT_NAME_MATCH_ARTICLE_PREFIX = "la "

_REQUIRED_DERIVE_KEYS = (
    "nodes_content_base64",
    "edges_content_base64",
    "run_id",
    "params_digest",
    "code_ref",
    "inputs",
)
_ENDPOINT_NAME_MATCH_REQUIRED_KEYS = ("node_match_property", "endpoint_property")

_FeatureCollectionModel = FeatureCollection[Feature[Geometry, dict[str, Any]]]


def _validate_geometry(raw: dict[str, Any], *, name: str) -> dict[str, Any]:
    """RFC 7946 vía `geojson-pydantic` — la instancia parseada se descarta;
    solo el veredicto pase/falle sobrevive como assertion."""
    try:
        _FeatureCollectionModel.model_validate(raw)
    except ValidationError as exc:
        errors = exc.errors(
            include_url=False, include_context=False, include_input=False
        )
        return {"name": name, "passed": False, "detail": {"errors": errors[:10]}}
    return {"name": name, "passed": True, "detail": None}


def _validate_tabular(
    features: list[dict[str, Any]], id_property: str
) -> dict[str, Any]:
    """Tabular vía `pandera` sobre las propiedades de los nodos: el ID
    estable debe existir, ser entero y único — sin eso el orden estable del
    punto 1 del determinismo no tiene sobre qué apoyarse."""
    schema = pa.DataFrameSchema(
        {id_property: pa.Column(int, unique=True, nullable=False)}
    )
    table = pd.DataFrame([f.get("properties") or {} for f in features])
    try:
        schema.validate(table)
    except SchemaError as exc:
        return {
            "name": "tabular_schema_valid",
            "passed": False,
            "detail": {"error": str(exc)},
        }
    return {"name": "tabular_schema_valid", "passed": True, "detail": None}


def _line_endpoints(geometry: dict[str, Any]) -> tuple[list[float], list[float]]:
    kind = geometry["type"]
    coords = geometry["coordinates"]
    if kind == "LineString":
        return coords[0], coords[-1]
    if kind == "MultiLineString":
        return coords[0][0], coords[-1][-1]
    msg = f"blite.ingesta.geojson.to_graph: geometría de arista no soportada: {kind!r}"
    raise ValueError(msg)


def _nearest_node(
    point: list[float], node_coords: list[tuple[float, float]]
) -> tuple[int, float]:
    best_index = 0
    best_distance = math.inf
    for index, (x, y) in enumerate(node_coords):
        distance = math.hypot(point[0] - x, point[1] - y)
        if distance < best_distance:
            best_distance = distance
            best_index = index
    return best_index, best_distance


def _decode_feature_collection(content_base64: str) -> dict[str, Any]:
    payload: Any = json.loads(base64.b64decode(content_base64))
    return payload


def _build_nodes(
    node_features: list[dict[str, Any]], id_property: str
) -> tuple[dict[str, dict[str, Any]], list[tuple[float, float]]]:
    sorted_nodes = sorted(node_features, key=lambda f: f["properties"][id_property])
    node_coords = [
        (f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][1])
        for f in sorted_nodes
    ]
    nodos = {
        str(index): {
            "source_ref": feature["properties"][id_property],
            "coordinates": list(feature["geometry"]["coordinates"]),
            "properties": feature["properties"],
        }
        for index, feature in enumerate(sorted_nodes)
    }
    return nodos, node_coords


def _build_edges(
    edge_features: list[dict[str, Any]],
    id_property: str,
    node_coords: list[tuple[float, float]],
) -> tuple[list[list[Any]], dict[str, Any], dict[str, Any]]:
    sorted_edges = sorted(edge_features, key=lambda f: f["properties"][id_property])
    aristas: list[list[Any]] = []
    max_endpoint_distance = 0.0
    self_loop_count = 0
    for feature in sorted_edges:
        first, last = _line_endpoints(feature["geometry"])
        i, distance_i = _nearest_node(first, node_coords)
        j, distance_j = _nearest_node(last, node_coords)
        max_endpoint_distance = max(max_endpoint_distance, distance_i, distance_j)
        if i == j:
            self_loop_count += 1
        aristas.append([i, j, 1])

    within_tolerance = max_endpoint_distance <= _ENDPOINT_SNAP_TOLERANCE_DEG
    tolerance_assertion = {
        "name": "edge_endpoints_within_tolerance",
        "passed": within_tolerance,
        "detail": None
        if within_tolerance
        else {
            "max_endpoint_distance_deg": max_endpoint_distance,
            "tolerance_deg": _ENDPOINT_SNAP_TOLERANCE_DEG,
        },
    }
    no_self_loop_assertion = {
        "name": "no_self_loop_edges",
        "passed": self_loop_count == 0,
        "detail": None
        if self_loop_count == 0
        else {"self_loop_count": self_loop_count},
    }
    return aristas, tolerance_assertion, no_self_loop_assertion


def _skipped_topology_assertions() -> tuple[dict[str, Any], dict[str, Any]]:
    """Con forma inválida la derivación no corre — coordenadas/índices no
    son de fiar. Ambas assertions de topología quedan `passed=False` con el
    motivo, nada se oculta (spec §Validación en frontera)."""
    detail = {"reason": "skipped: upstream schema validation failed"}
    return (
        {"name": "edge_endpoints_within_tolerance", "passed": False, "detail": detail},
        {"name": "no_self_loop_edges", "passed": False, "detail": detail},
    )


def _skipped_endpoint_name_match_assertion() -> dict[str, Any]:
    """Equivalente de `_skipped_topology_assertions` para la estrategia
    `endpoint-name-match` — misma honestidad, un solo assertion propio."""
    return {
        "name": "edge_endpoint_names_resolved",
        "passed": False,
        "detail": {"reason": "skipped: upstream schema validation failed"},
    }


def _normalize_name(value: str) -> str:
    """NFKD -> ASCII (descarta diacríticos) -> minúsculas -> strip — matching
    de nombres insensible a acentos/mayúsculas entre dos datasets."""
    flat = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return flat.lower().strip()


def _parse_endpoint_token(token: str, node_keys: frozenset[str]) -> str | None:
    """Normaliza un token crudo de extremo de arista a una clave de nodo
    conocida, o `None` si no resuelve. Quita dígitos finales (sufijo de
    número de circuito paralelo) antes de intentar el match directo y, si
    falla, el fallback con artículo prefijado."""
    candidate = _normalize_name(token).rstrip("0123456789").strip()
    if candidate in node_keys:
        return candidate
    prefixed = f"{_ENDPOINT_NAME_MATCH_ARTICLE_PREFIX}{candidate}"
    if prefixed in node_keys:
        return prefixed
    return None


def _resolve_edge_endpoints(
    raw_value: str | None, separator: str, node_keys: frozenset[str]
) -> tuple[str, str] | None:
    """`raw_value` dividido por `separator` en exactamente 2 tokens, ambos
    resolviendo a nodos DISTINTOS — cualquier otro caso (no son 2 tokens, un
    token no resuelve, o resuelven al mismo nodo) es `None` (arista
    descartada, contabilizada por el caller — nunca silenciosa)."""
    parts = (raw_value or "").split(separator)
    if len(parts) != 2:
        return None
    first = _parse_endpoint_token(parts[0], node_keys)
    second = _parse_endpoint_token(parts[1], node_keys)
    if first is None or second is None or first == second:
        return None
    return (first, second) if first < second else (second, first)


def _build_endpoint_name_match_node_index(
    node_features: list[dict[str, Any]], id_property: str, node_match_property: str
) -> dict[str, dict[str, Any]]:
    """normalized(node_match_property) -> feature de nodo. Ordenado por
    `id_property` primero (determinismo punto 1) y first-wins ante nombres
    normalizados duplicados."""
    sorted_nodes = sorted(node_features, key=lambda f: f["properties"][id_property])
    index: dict[str, dict[str, Any]] = {}
    for feature in sorted_nodes:
        key = _normalize_name(feature["properties"][node_match_property])
        index.setdefault(key, feature)
    return index


def _aggregate_endpoint_name_match_edges(
    edge_features: list[dict[str, Any]],
    *,
    id_property: str,
    endpoint_property: str,
    endpoint_separator: str,
    weight_property: str | None,
    node_keys: frozenset[str],
) -> tuple[dict[tuple[str, str], dict[str, int]], int]:
    """Agrega circuitos paralelos entre el mismo par de nodos resueltos —
    devuelve el mapa (par -> {circuits, weight_sum}) más cuántas aristas se
    descartaron por endpoint desconocido/inválido."""
    sorted_edges = sorted(edge_features, key=lambda f: f["properties"][id_property])
    aggregate: dict[tuple[str, str], dict[str, int]] = {}
    discarded_count = 0
    for feature in sorted_edges:
        raw_value = feature["properties"].get(endpoint_property)
        endpoints = _resolve_edge_endpoints(raw_value, endpoint_separator, node_keys)
        if endpoints is None:
            discarded_count += 1
            continue
        entry = aggregate.setdefault(endpoints, {"circuits": 0, "weight_sum": 0})
        entry["circuits"] += 1
        if weight_property is not None:
            entry["weight_sum"] += int(feature["properties"][weight_property])
    return aggregate, discarded_count


def _endpoint_name_match_topology(
    node_features: list[dict[str, Any]],
    edge_features: list[dict[str, Any]],
    *,
    id_property: str,
    node_match_property: str,
    endpoint_property: str,
    endpoint_separator: str,
    weight_property: str | None,
) -> tuple[dict[str, dict[str, Any]], list[list[Any]], dict[str, Any]]:
    node_index = _build_endpoint_name_match_node_index(
        node_features, id_property, node_match_property
    )
    node_keys = frozenset(node_index.keys())
    aggregate, discarded_count = _aggregate_endpoint_name_match_edges(
        edge_features,
        id_property=id_property,
        endpoint_property=endpoint_property,
        endpoint_separator=endpoint_separator,
        weight_property=weight_property,
        node_keys=node_keys,
    )

    # Solo los nodos que resuelven >=1 arista entran a la salida — un nodo
    # del snapshot que ninguna arista referencia queda fuera, honestamente.
    matched_keys = {key for pair in aggregate for key in pair}
    ordered_keys = sorted(
        matched_keys, key=lambda key: node_index[key]["properties"][id_property]
    )
    key_to_index = {key: position for position, key in enumerate(ordered_keys)}

    nodos = {
        str(position): {
            "source_ref": node_index[key]["properties"][id_property],
            "coordinates": list(node_index[key]["geometry"]["coordinates"]),
            "properties": node_index[key]["properties"],
        }
        for key, position in key_to_index.items()
    }
    aristas: list[list[Any]] = []
    for (a, b), entry in aggregate.items():
        i, j = sorted((key_to_index[a], key_to_index[b]))
        weight = entry["circuits"] if weight_property is None else entry["weight_sum"]
        aristas.append([i, j, weight])
    aristas.sort()

    resolved_assertion = {
        "name": "edge_endpoint_names_resolved",
        "passed": discarded_count == 0,
        "detail": None
        if discarded_count == 0
        else {
            "discarded_count": discarded_count,
            "total_edge_features": len(edge_features),
        },
    }
    return nodos, aristas, resolved_assertion


def _endpoint_name_match_params(inputs: dict[str, Any]) -> dict[str, Any]:
    weight_property = inputs.get("weight_property")
    return {
        "node_match_property": str(inputs["node_match_property"]),
        "endpoint_property": str(inputs["endpoint_property"]),
        "endpoint_separator": str(
            inputs.get("endpoint_separator", _DEFAULT_ENDPOINT_SEPARATOR)
        ),
        "weight_property": None if weight_property is None else str(weight_property),
    }


def _derive_topology(
    *,
    shape_valid: bool,
    node_features: list[dict[str, Any]],
    edge_features: list[dict[str, Any]],
    id_property: str,
    edge_strategy: str,
    strategy_params: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[list[Any]], tuple[dict[str, Any], ...]]:
    if edge_strategy == _EDGE_STRATEGY_ENDPOINT_NAME_MATCH:
        if not shape_valid:
            return {}, [], (_skipped_endpoint_name_match_assertion(),)
        nodos, aristas, resolved_assertion = _endpoint_name_match_topology(
            node_features,
            edge_features,
            id_property=id_property,
            **_endpoint_name_match_params(strategy_params),
        )
        return nodos, aristas, (resolved_assertion,)

    if edge_strategy != _EDGE_STRATEGY_NEAREST_NEIGHBOR:
        msg = (
            "blite.ingesta.geojson.to_graph: edge_strategy desconocida: "
            f"{edge_strategy!r}"
        )
        raise ValueError(msg)

    if not shape_valid:
        return {}, [], _skipped_topology_assertions()

    nodos, node_coords = _build_nodes(node_features, id_property)
    aristas, tolerance_assertion, no_self_loop_assertion = _build_edges(
        edge_features, id_property, node_coords
    )
    return nodos, aristas, (tolerance_assertion, no_self_loop_assertion)


def _build_recipe(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "capability": "blite.ingesta.geojson.to_graph",
        "version": "0.1.0",
        "params_digest": str(inputs["params_digest"]),
        "code_ref": str(inputs["code_ref"]),
    }


def derive_graph(inputs: dict[str, Any]) -> dict[str, Any]:
    """Implementación de `GeojsonToGraph.invoke` — ver `tool.py` para el
    manifest y el wrapper de `Capability`."""
    missing = [key for key in _REQUIRED_DERIVE_KEYS if key not in inputs]
    if missing:
        msg = f"blite.ingesta.geojson.to_graph: faltan llaves requeridas {missing}"
        raise ValueError(msg)

    edge_strategy = str(inputs.get("edge_strategy", _DEFAULT_EDGE_STRATEGY))
    if edge_strategy == _EDGE_STRATEGY_ENDPOINT_NAME_MATCH:
        missing_strategy = [
            key for key in _ENDPOINT_NAME_MATCH_REQUIRED_KEYS if key not in inputs
        ]
        if missing_strategy:
            msg = (
                "blite.ingesta.geojson.to_graph: edge_strategy="
                f"{edge_strategy!r} requiere las llaves {missing_strategy}"
            )
            raise ValueError(msg)

    id_property = str(inputs.get("node_id_property", _DEFAULT_NODE_ID_PROPERTY))
    nodes_raw = _decode_feature_collection(inputs["nodes_content_base64"])
    edges_raw = _decode_feature_collection(inputs["edges_content_base64"])
    node_features: list[dict[str, Any]] = nodes_raw["features"]
    edge_features: list[dict[str, Any]] = edges_raw["features"]

    node_geometry_assertion = _validate_geometry(
        nodes_raw, name="node_geojson_schema_valid"
    )
    edge_geometry_assertion = _validate_geometry(
        edges_raw, name="edge_geojson_schema_valid"
    )
    tabular_assertion = _validate_tabular(node_features, id_property)
    shape_valid = (
        node_geometry_assertion["passed"]
        and edge_geometry_assertion["passed"]
        and tabular_assertion["passed"]
    )

    nodos, aristas, strategy_assertions = _derive_topology(
        shape_valid=shape_valid,
        node_features=node_features,
        edge_features=edge_features,
        id_property=id_property,
        edge_strategy=edge_strategy,
        strategy_params=inputs,
    )

    graph = {"n_nodos": len(nodos), "aristas": aristas, "nodos": nodos}
    provenance = {
        "kind": "derivation",
        "inputs": tuple(inputs["inputs"]),
        "recipe": _build_recipe(inputs),
        "run_id": str(inputs["run_id"]),
        "assertions": (
            node_geometry_assertion,
            edge_geometry_assertion,
            tabular_assertion,
            *strategy_assertions,
        ),
    }
    return {"graph": graph, "provenance": provenance}
