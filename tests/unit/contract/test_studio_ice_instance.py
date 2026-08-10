"""Anti-drift de la proyección instancia→Studio (V1/M18).

El overlay del mapa reconcilia `bus_ids` (índices de la instancia derivada)
con features geográficas nombradas usando el mapa `nodos` que la instancia YA
estampó. Este test evita la única forma en que esa reconciliación puede
mentir: que el corpus cambie y la copia del Studio se quede vieja, pintando
una isla sobre las subestaciones equivocadas.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_OUT = _REPO / "apps" / "studio" / "src" / "fixtures" / "ice" / "instancia.json"
_CORPUS = _REPO / "knowledge" / "islanding" / "corpus" / "ice-uniforme.json"


def _load_generator() -> object:
    path = _REPO / "scripts" / "gen-studio-ice-instance.py"
    spec = importlib.util.spec_from_file_location("gen_studio_ice_instance", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lo_commiteado_es_lo_que_el_generador_produce_hoy() -> None:
    module = _load_generator()
    expected = module.serialize(module.build())  # type: ignore[attr-defined]
    assert _OUT.read_text(encoding="utf-8") == expected


def test_el_digest_es_el_de_la_instancia_estampada() -> None:
    """La proyección declara CUÁL instancia reconcilia — sin el digest, un
    overlay no podría decir si está pintando la red que el run usó."""
    proyectada = json.loads(_OUT.read_text(encoding="utf-8"))
    estampada = json.loads(_CORPUS.read_text(encoding="utf-8"))
    assert proyectada["digest"] == estampada["digest"]
    assert proyectada["nodos"] == estampada["nodos"]


def test_la_aritmetica_honesta_68_de_70_sigue_declarada() -> None:
    """68 nodos en el componente conexo, de 70 subestaciones del snapshot —
    el desajuste es del dato, y el overlay lo muestra en vez de esconderlo."""
    proyectada = json.loads(_OUT.read_text(encoding="utf-8"))
    assert proyectada["n_nodos"] == 68
    assert len(proyectada["nodos"]) == 68
