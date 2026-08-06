"""Contrato de costura de la proyección OTel — anti-drift del golden (S-F/#128).

`docs/specs/observabilidad-proyeccion.md` §"Tests de contrato" +
`docs/specs/README.md` §"Fixtures de costura — un solo origen":

1. lo commiteado == lo que el generador produce HOY (falla-fuerte);
2. el golden se re-deriva del stream que él mismo lleva — un fixture que no se
   pueda recomputar de su propia entrada no prueba nada;
3. espejo de Studio NO aplica: el consumidor de esta costura es un collector
   OTLP, no el Studio (la spec lo declara explícitamente).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, cast

_REPO = Path(__file__).resolve().parents[3]
_FIXTURE = (
    _REPO / "tests" / "fixtures" / "contract" / "observabilidad" / "trace-example.json"
)
_GENERADOR = _REPO / "scripts" / "gen-contract-fixtures-observabilidad.py"


def _load_generator() -> Any:
    """El nombre lleva guiones ⇒ no es importable como módulo."""
    spec = importlib.util.spec_from_file_location("gen_fixtures_obs", _GENERADOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_el_fixture_commiteado_es_el_que_el_generador_produce_hoy() -> None:
    """Anti-drift: si esto falla, corre el generador — no edites el fixture."""
    generator = _load_generator()
    from chimera_otel.projection import project_run, span_id_for

    stream = cast(list[dict[str, Any]], generator.build_stream())
    plan = project_run(stream)
    assert plan is not None

    esperado = {
        "_comentario": (
            "Golden de la proyección evento→span (S-F §3/§4). Generado por "
            "scripts/gen-contract-fixtures-observabilidad.py — no editar a mano."
        ),
        "run_id": plan.run_id,
        "trace_id": plan.trace_id.hex(),
        "stream": stream,
        "spans": {
            span.anchor: {
                "name": span.name,
                "span_id": span_id_for(plan.run_id, span.anchor).hex(),
                "parent_anchor": span.parent_anchor,
                "status": span.status,
            }
            for span in plan.spans
        },
    }
    en_disco = json.dumps(esperado, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert _FIXTURE.read_text(encoding="utf-8") == en_disco


def test_el_golden_cubre_las_cinco_clases_de_span_de_la_tabla() -> None:
    """§3 tiene cinco filas con span propio: un golden que solo cubriera una
    dejaría el resto del mapeo sin testigo."""
    golden = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    nombres = {span["name"] for span in golden["spans"].values()}
    assert nombres == {"run", "step", "capability", "gen_ai", "verification"}
