"""Validacion INDEPENDIENTE del corpus `ieee6` (pandapower.networks.case6ww).

Instancia REAL de 6 nodos agregada por la receta congelada del corpus
(scripts/gen_corpus_islanding.py, `.superpowers/sdd/task3-brief.md` — D5:
stand-in reproducible mientras la instancia ICE "provincia" esta diferida).
n=6 <= 14 -> doble ancla (CP-SAT + fuerza bruta) aplica (islanding/01 SS1.4).

Este test NO confia en el archivo: recomputa el digest canonico, recorre las
32 asignaciones (2**5, x0=0) con su propio `cut_value`, y compara contra
`optimo`/`asignacion_canonica` embebidos — mismo principio de doble ancla
independiente que el propio generador.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import networkx as nx
import pytest

_N_NODOS = 6
_CONVENCIONES = ("uniforme", "flujo")


def _find_corpus() -> Path:
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        candidate = base / "knowledge" / "islanding" / "corpus"
        if candidate.is_dir():
            return candidate
    msg = "corpus de islanding no encontrado sobre este archivo"
    raise FileNotFoundError(msg)


def _cargar_registro(convencion: str) -> dict[str, Any]:
    ruta = _find_corpus() / f"ieee6-{convencion}.json"
    return json.loads(ruta.read_text(encoding="utf-8"))


def _digest_canonico(registro: dict[str, Any]) -> str:
    sin_digest = {k: v for k, v in registro.items() if k != "digest"}
    canonico = json.dumps(
        sin_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _cut_value(aristas: list[list[int]], x: tuple[int, ...]) -> int:
    return sum(w for i, j, w in aristas if x[i] != x[j])


def _optimo_fuerza_bruta(aristas: list[list[int]]) -> tuple[int, list[int]]:
    """Enumeracion independiente 2**(n-1) con x0=0 — no reusa el generador."""
    mejor, mejor_x = -1, None
    for bits in itertools.product((0, 1), repeat=_N_NODOS - 1):
        x = (0, *bits)
        v = _cut_value(aristas, x)
        if v > mejor:
            mejor, mejor_x = v, x
    assert mejor_x is not None
    return mejor, list(mejor_x)


@pytest.mark.parametrize("convencion", _CONVENCIONES)
class TestCorpusIeee6:
    def test_archivo_existe_y_digest_reproduce_canonico(self, convencion: str) -> None:
        registro = _cargar_registro(convencion)

        assert registro["digest"] == _digest_canonico(registro)

    def test_n_nodos_es_6(self, convencion: str) -> None:
        registro = _cargar_registro(convencion)

        assert registro["n_nodos"] == _N_NODOS

    def test_aristas_ordenadas_enteras_y_grafo_conexo(self, convencion: str) -> None:
        registro = _cargar_registro(convencion)
        aristas = registro["aristas"]

        for i, j, w in aristas:
            assert isinstance(i, int)
            assert isinstance(j, int)
            assert isinstance(w, int)
            assert i < j

        pares = [(i, j) for i, j, _ in aristas]
        assert pares == sorted(pares)

        grafo = nx.Graph((i, j) for i, j, _ in aristas)
        assert grafo.number_of_nodes() == _N_NODOS
        assert nx.is_connected(grafo)

    def test_optimo_coincide_con_fuerza_bruta_independiente(
        self, convencion: str
    ) -> None:
        registro = _cargar_registro(convencion)
        aristas = registro["aristas"]

        optimo_independiente, _ = _optimo_fuerza_bruta(aristas)

        assert registro["optimo"] == optimo_independiente
        assert registro["solver_status"] == "OPTIMAL"

    def test_asignacion_canonica_reproduce_el_optimo(self, convencion: str) -> None:
        registro = _cargar_registro(convencion)
        aristas = registro["aristas"]
        asignacion = tuple(registro["asignacion_canonica"])

        assert _cut_value(aristas, asignacion) == registro["optimo"]
