#!/usr/bin/env python3
"""Genera el corpus ICE (Max-Cut, sin prueba de optimalidad) desde los
snapshots ICE del portal (`ice-subestaciones.geojson` / `ice-lineas-transmision.geojson`,
YA NO commiteados en el árbol -- ver el párrafo de reproducibilidad más abajo).

Correr desde la raiz del repo:  uv run python scripts/gen_corpus_ice.py --raw-dir <dir>
Salida: knowledge/islanding/corpus/ice-{uniforme,voltaje}.json

Paridad con `reto1-vanilla/scripts/build_cr_instances.py::load_national_graph`
(mismo parseo del campo `Circuito`: normaliza acentos/mayusculas, quita el
sufijo numerico de circuito paralelo, intenta el fallback "la <nombre>"),
salvo que aqui la derivacion corre A TRAVES de la capability real
`blite.ingesta.geojson.to_graph` con `edge_strategy="endpoint-name-match"`
(capabilities/ingesta/src/blite_cap_ingesta/geojson_to_graph.py) en vez de
un script que evada la capability — los nombres de campo concretos de ICE
("Circuito"/"Subestacio"/"Voltaje") viajan como PARAMS de la invocacion,
nunca en el manifest generico (ADR-029).

Honestidad de escala: de las 70 subestaciones del snapshot, 68 quedan en el
UNICO componente conexo que forman las lineas parseables; 2 quedan aisladas
(ningun `Circuito` resuelve hacia ellas); 8 lineas se descartan por endpoint
desconocido. `n_nodos=68` (el grafo REAL, no las 70 del snapshot) y
`optimo=None` -- n=68 excede el umbral de doble ancla de fuerza bruta
(islanding/01 SS1.4, `FUERZA_BRUTA_MAX_N=14` en `gen_corpus_islanding.py`) y
esta generacion no corre ningun solver de Max-Cut sobre la red completa; la
razon queda en `notas`, nunca oculta.

Reproducibilidad air-gap (histórica): este script leía los snapshots YA
COMMITEADOS en `knowledge/islanding/raw/ice-{subestaciones,lineas-transmision}.geojson`
-- nunca la URL del FeatureServer en tiempo de generación. Decisión #173.1
(opción b, `NOTICE` §2): esa copia verbatim del portal SALIÓ del árbol -- la
licencia de redistribución de esos bytes concretos seguía sin confirmar, y el
catálogo de datasets publicados ya no depende de ellos. Lo que se conserva es
lo derivado (`knowledge/islanding/corpus/ice-*.json`, con
`ExternalSourceProvenance` citando los snapshots por digest) bajo el mismo
razonamiento que `NOTICE` §1 ya usa para pandapower.

Este script sigue siendo la receta completa: quien tenga los snapshots del
portal (`datos-ice-se.opendata.arcgis.com`, datasets `Subestaciones` y
`LineasDeTransmision`) puede apuntar `--raw-dir`/`$CHIMERA_ICE_RAW_DIR` a un
directorio propio y re-derivar, comparando el digest resultante contra el
corpus congelado. Si los snapshots no están donde se los busca, falla fuerte
y legible (`require_snapshots`) en vez de un `FileNotFoundError` críptico.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import networkx as nx

from blite.verification.provenance import (
    DerivationProvenance,
    ExternalSourceProvenance,
    parse_provenance,
)
from blite_cap_ingesta import GeojsonToGraph

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "knowledge" / "islanding" / "corpus"
DEFAULT_RAW_DIR = REPO / "knowledge" / "islanding" / "raw"
RAW_DIR_ENV_VAR = "CHIMERA_ICE_RAW_DIR"
NODES_FILENAME = "ice-subestaciones.geojson"
EDGES_FILENAME = "ice-lineas-transmision.geojson"

RETRIEVED_AT = datetime(2026, 7, 23, tzinfo=UTC)
DESCARGADO = "2026-07-23"
SOURCES = {
    "lineas": "https://services1.arcgis.com/cW2GfO4rBCLoFwgj/arcgis/rest/services/LineasDeTransmision/FeatureServer",
    "subestaciones": "https://services1.arcgis.com/cW2GfO4rBCLoFwgj/arcgis/rest/services/Subestaciones/FeatureServer",
    "portal": "https://datos-ice-se.opendata.arcgis.com",
}
CONVENTIONS: dict[str, str | None] = {"uniforme": None, "voltaje": "Voltaje"}
DEFINICION_PESO = {
    "uniforme": "1 por circuito paralelo",
    "voltaje": "suma de niveles de tension (kV) de los circuitos paralelos",
}
EXPECTED_N_NODOS = 68
EXPECTED_ARISTAS = 90
NOTAS = (
    "n=68>14: sin prueba de optimalidad (fuera del umbral de doble ancla de "
    "fuerza bruta usado en el resto del corpus; no se corrio ningun solver "
    "de Max-Cut sobre esta instancia)",
    "70 subestaciones en snapshot; 68 en el componente conexo; 2 aisladas "
    "por nomenclatura; 8 lineas descartadas por endpoint desconocido",
)


class IceSnapshotsMissingError(FileNotFoundError):
    """Faltan los snapshots verbatim del portal del ICE (decisión #173.1)."""


def resolve_raw_dir(raw_dir_arg: str | None = None) -> Path:
    """Prioridad: `--raw-dir` explícito > `$CHIMERA_ICE_RAW_DIR` > default del árbol.

    El default (`knowledge/islanding/raw/`) ya no tiene los snapshots desde
    la decisión #173.1 -- queda como valor por defecto igual porque es donde
    vivían y es donde alguien con los datos del portal probablemente los
    pondría de nuevo."""
    if raw_dir_arg:
        return Path(raw_dir_arg)
    env_value = os.environ.get(RAW_DIR_ENV_VAR)
    if env_value:
        return Path(env_value)
    return DEFAULT_RAW_DIR


def require_snapshots(raw_dir: Path) -> tuple[Path, Path]:
    """Verifica que los dos snapshots del portal existan en `raw_dir`.

    Falla fuerte y legible en vez del `FileNotFoundError` críptico de
    Python: dice qué faltó, por qué (decisión #173.1 -- la copia verbatim
    del portal ya no viaja en el árbol, licencia de redistribución sin
    confirmar), de dónde bajarla, dónde ponerla, y que la receta de
    derivación + los digests del corpus congelado siguen intactos para
    re-derivar y comprobar."""
    nodes_path = raw_dir / NODES_FILENAME
    edges_path = raw_dir / EDGES_FILENAME
    faltantes = [p for p in (nodes_path, edges_path) if not p.is_file()]
    if faltantes:
        nombres = " y ".join(p.name for p in faltantes)
        msg = (
            f"No encontré {nombres} en {raw_dir}.\n"
            "\n"
            "La copia verbatim de los datasets del portal del ICE ya NO "
            "viaja en este repo (decisión #173.1, opción b -- ver `NOTICE` "
            "§2 y `docs/pre-flip-checklist.md` §4.2): la licencia para "
            "redistribuir esos bytes concretos seguía sin confirmar, y la "
            "plataforma no depende de ellos como dataset publicado.\n"
            "\n"
            "Para re-derivar el corpus ICE:\n"
            "  1. Bajá los datasets 'Subestaciones' y 'LineasDeTransmision' "
            "del portal abierto del ICE: "
            "https://datos-ice-se.opendata.arcgis.com\n"
            f"  2. Guardalos como {NODES_FILENAME} / {EDGES_FILENAME} en un "
            "directorio propio.\n"
            "  3. Corré este script apuntando ahí, por argumento:\n"
            "       uv run python scripts/gen_corpus_ice.py --raw-dir <dir>\n"
            "     o por variable de entorno:\n"
            f"       {RAW_DIR_ENV_VAR}=<dir> "
            "uv run python scripts/gen_corpus_ice.py\n"
            "\n"
            "La receta de derivación (blite.ingesta.geojson.to_graph, los "
            "params exactos, y los digests esperados) sigue completa en "
            "este archivo y en knowledge/islanding/01-corpus-benchmarks.md: "
            "cualquiera con los datos del portal puede re-derivar y "
            "comparar el digest resultante contra "
            "knowledge/islanding/corpus/ice-*.json, que se queda como está."
        )
        raise IceSnapshotsMissingError(msg)
    return nodes_path, edges_path


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _external_source_provenance(uri: str) -> dict[str, Any]:
    """Construye Y valida via el modelo Pydantic real (round-trip, mismo
    espiritu que `scripts/gen-fixtures-ingesta.py`) antes de embeber el dict
    plano en el corpus -- nunca se arma el dict a mano sin pasar por el tipo."""
    provenance = ExternalSourceProvenance(
        uri=uri,
        retrieved_at=RETRIEVED_AT,
        content_type="application/geo+json",
        http_status=200,
    )
    dumped = provenance.model_dump(mode="json")
    parsed = parse_provenance(dumped)
    if not isinstance(parsed, ExternalSourceProvenance):
        msg = "round-trip de ExternalSourceProvenance produjo otra rama"
        raise TypeError(msg)
    return dumped


def _invoke_to_graph(
    weight_property: str | None, run_id: str, nodes_path: Path, edges_path: Path
) -> dict[str, Any]:
    params_digest_source = json.dumps(
        {"edge_strategy": "endpoint-name-match", "weight_property": weight_property},
        sort_keys=True,
    )
    inputs = {
        "nodes_content_base64": _b64(nodes_path),
        "edges_content_base64": _b64(edges_path),
        "node_id_property": "FID",
        "edge_strategy": "endpoint-name-match",
        "node_match_property": "Subestacio",
        "endpoint_property": "Circuito",
        "endpoint_separator": "-",
        "weight_property": weight_property,
        "run_id": run_id,
        "params_digest": "sha256:"
        + hashlib.sha256(params_digest_source.encode("utf-8")).hexdigest(),
        "code_ref": "git:HEAD",
        "inputs": [
            {
                "ref": "snapshot:ice-subestaciones",
                "digest": "sha256:" + _sha256_hex(nodes_path),
            },
            {
                "ref": "snapshot:ice-lineas-transmision",
                "digest": "sha256:" + _sha256_hex(edges_path),
            },
        ],
    }
    result = GeojsonToGraph().invoke(inputs)
    parsed = parse_provenance(result["provenance"])
    if not isinstance(parsed, DerivationProvenance):
        msg = "round-trip de DerivationProvenance produjo otra rama"
        raise TypeError(msg)
    return result


def _verify_topology(graph: dict[str, Any]) -> None:
    n = graph["n_nodos"]
    aristas = graph["aristas"]
    if n != EXPECTED_N_NODOS:
        msg = f"ICE: n_nodos esperado {EXPECTED_N_NODOS}, obtuve {n} -- drift en el snapshot o el parseo"
        raise AssertionError(msg)
    if len(aristas) != EXPECTED_ARISTAS:
        msg = f"ICE: aristas esperadas {EXPECTED_ARISTAS}, obtuve {len(aristas)}"
        raise AssertionError(msg)
    grafo = nx.Graph((i, j) for i, j, _w in aristas)
    if grafo.number_of_nodes() != n or not nx.is_connected(grafo):
        msg = "ICE: el grafo derivado no es un unico componente conexo de 68 nodos"
        raise AssertionError(msg)


def _con_digest(registro: dict[str, Any]) -> dict[str, Any]:
    canonico = json.dumps(
        registro, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return {**registro, "digest": hashlib.sha256(canonico.encode("utf-8")).hexdigest()}


def _build_record(
    convention: str,
    weight_property: str | None,
    nodes_path: Path,
    edges_path: Path,
) -> dict[str, Any]:
    result = _invoke_to_graph(
        weight_property,
        run_id=f"gen-corpus-ice-{convention}",
        nodes_path=nodes_path,
        edges_path=edges_path,
    )
    graph = result["graph"]
    _verify_topology(graph)

    aristas = [[int(i), int(j), int(w)] for i, j, w in graph["aristas"]]
    nodos_por_indice = {
        indice: meta["properties"]["Subestacio"]
        for indice, meta in graph["nodos"].items()
    }
    external_sources = {
        "ice-subestaciones": _external_source_provenance(SOURCES["subestaciones"]),
        "ice-lineas-transmision": _external_source_provenance(SOURCES["lineas"]),
    }

    registro = {
        "instancia": "ice",
        "convencion": convention,
        "n_nodos": graph["n_nodos"],
        "aristas": aristas,
        "escala": 1,
        "optimo": None,
        "asignacion_canonica": None,
        "metodos": [],
        "solver_status": "NOT_ATTEMPTED",
        "notas": list(NOTAS),
        "nodos": nodos_por_indice,
        "fuente": SOURCES,
        "descargado": DESCARGADO,
        "definicion_peso": DEFINICION_PESO[convention],
        "provenance": {
            "external_sources": external_sources,
            "derivation": result["provenance"],
        },
    }
    return _con_digest(registro)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Genera knowledge/islanding/corpus/ice-{uniforme,voltaje}.json "
            "desde los snapshots del portal del ICE."
        )
    )
    parser.add_argument(
        "--raw-dir",
        default=None,
        help=(
            "Directorio con "
            f"{NODES_FILENAME} / {EDGES_FILENAME}. Default: "
            f"${RAW_DIR_ENV_VAR} si está seteada, si no "
            f"{DEFAULT_RAW_DIR.relative_to(REPO)} (vacío desde la decisión "
            "#173.1 -- ver el docstring del módulo)."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    raw_dir = resolve_raw_dir(args.raw_dir)
    try:
        nodes_path, edges_path = require_snapshots(raw_dir)
    except IceSnapshotsMissingError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for convention, weight_property in CONVENTIONS.items():
        record = _build_record(convention, weight_property, nodes_path, edges_path)
        path = OUT_DIR / f"ice-{convention}.json"
        path.write_text(
            json.dumps(record, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        rows.append(
            (
                record["instancia"],
                convention,
                record["n_nodos"],
                len(record["aristas"]),
                record["digest"][:12],
            )
        )
        print(f"escrito: {path.relative_to(REPO)}")

    print()
    print(f"{'instancia':10} {'convencion':10} {'n':>3} {'|E|':>4} digest")
    for row in rows:
        print(f"{row[0]:10} {row[1]:10} {row[2]:>3} {row[3]:>4} {row[4]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
