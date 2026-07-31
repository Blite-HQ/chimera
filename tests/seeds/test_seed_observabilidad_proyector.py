"""Seed del proyector de observabilidad OTel (S-F, decisión #127 — C-11).

Contrato: docs/specs/observabilidad-proyeccion.md. El proyector es un
consumer standalone FUERA de blite.* (`projectors/otel/`, paquete
`chimera_otel`); sus trace/span-id son DETERMINISTAS (re-proyección ⇒ trazas
byte-idénticas). El xfail se retira cuando O3 lo implemente.

Directiva pyright per-file: el paquete objetivo no existe por diseño hasta
Fase 1; la directiva se retira junto con el xfail.
"""

# pyright: reportMissingImports=false, reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false

from __future__ import annotations

import hashlib

import pytest

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason=(
            "Fase 1 O3/M9: projectors/otel (chimera_otel) no existe todavía — "
            "docs/specs/observabilidad-proyeccion.md (#127)"
        ),
    ),
]


def _trace_id_esperado(run_id: str) -> bytes:
    """Recompute INDEPENDIENTE de la derivación §Contrato-4 (jamás importar
    la del proyector para verificarla contra sí misma)."""
    return hashlib.sha256(b"blite/otel-trace/v1\n" + run_id.encode()).digest()[:16]


def _span_id_esperado(run_id: str, ancla: str) -> bytes:
    return hashlib.sha256(
        b"blite/otel-span/v1\n" + f"{run_id}:{ancla}".encode()
    ).digest()[:8]


def test_trace_id_determinista_con_prefijo_de_dominio() -> None:
    from chimera_otel.projection import trace_id_for_run

    assert trace_id_for_run("run-1") == _trace_id_esperado("run-1")
    assert trace_id_for_run("run-1") == trace_id_for_run("run-1")
    assert trace_id_for_run("run-1") != trace_id_for_run("run-2")


def test_span_id_determinista_por_ancla() -> None:
    from chimera_otel.projection import span_id_for

    assert span_id_for("run-1", "step-1") == _span_id_esperado("run-1", "step-1")
    assert span_id_for("run-1", "step-1") != span_id_for("run-1", "step-2")


def test_frontera_c11_sin_imports_de_blite() -> None:
    """C-11: el proyector parsea wire JSON — jamás importa el engine. Se
    inspeccionan los imports del MÓDULO (sys.modules es compartido con el
    resto de la suite y no sirve de testigo)."""
    import ast
    import inspect

    import chimera_otel.projection as projection

    tree = ast.parse(inspect.getsource(projection))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any(alias.name.startswith("blite") for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith("blite")
