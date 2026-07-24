"""Tests de INVARIANTES para `scripts/import_nexus_runs.py` (B3 — evidencia
externa importada, docs/specs/evidencia-externa.md).

`scripts/` no es un paquete instalable — mismo patrón que
`tests/unit/experiment/test_exp_r_vs_p.py`: el módulo se carga por ruta con
`importlib.util.spec_from_file_location` y se envuelve tras un `Protocol`
tipado.

Dos grupos:
- `TestBitOrderAgainstTheRealCorpus`/`TestResolveBitOrders`: la lógica de
  determinación EMPÍRICA de `bit_order` (test G6 generalizado,
  `knowledge/quantum/08` §5) contra el grafo REAL de
  `knowledge/islanding/corpus/cr6-uniforme.json` (committeado en este repo,
  sin depender del espejo) con bitstrings tomados de corridas reales
  (`runs/nexus/cr6-uniforme-p1-s0-H2-1LE.json` del espejo — valores
  reproducidos aquí como literales, no leídos en el momento del test).
- `TestImportOnTheMirror`: el importador completo sobre las 19 corridas
  reales del espejo `reto1-vanilla` — SKIP si el espejo no está montado en
  esta máquina (portabilidad; en el entorno de desarrollo del equipo SÍ
  está montado y estos tests corren de verdad).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Protocol, cast

import pytest

from blite.verification.external_evidence import BitOrder

# Grafo REAL de cr6-uniforme (knowledge/islanding/corpus/cr6-uniforme.json):
# aristas (0,1),(0,3),(0,4),(0,5),(1,2),(3,4) peso 1, optimo=5,
# asignacion_canonica=[0,1,0,0,1,1].
_CR6_ARISTAS: list[list[int]] = [
    [0, 1, 1],
    [0, 3, 1],
    [0, 4, 1],
    [0, 5, 1],
    [1, 2, 1],
    [3, 4, 1],
]
_CR6_OPTIMO = 5


class _ImportModule(Protocol):
    def candidate_bit_orders(
        self, run: dict[str, Any], aristas: list[list[int]]
    ) -> tuple[BitOrder, ...]: ...

    def dominant_bit_orders(
        self, run: dict[str, Any], aristas: list[list[int]]
    ) -> tuple[BitOrder, ...]: ...

    def resolve_bit_orders(
        self, records: list[tuple[str, dict[str, Any], list[list[int]]]]
    ) -> dict[str, Any]: ...

    def run_import(self, mirror_dir: Path, corpus_dir: Path, out_dir: Path) -> Any: ...


def _find_repo_root() -> Path:
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        candidate = base / "scripts" / "import_nexus_runs.py"
        if candidate.is_file():
            return base
    msg = "scripts/import_nexus_runs.py no encontrado sobre este archivo"
    raise FileNotFoundError(msg)


def _load_module() -> _ImportModule:
    repo = _find_repo_root()
    script_path = repo / "scripts" / "import_nexus_runs.py"
    spec = importlib.util.spec_from_file_location("import_nexus_runs", script_path)
    if spec is None:
        msg = f"no se pudo construir un spec de import para {script_path}"
        raise ImportError(msg)
    loader = spec.loader
    if loader is None:
        msg = f"el spec de {script_path} no tiene loader"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    # `@dataclass` (Python 3.12) resuelve anotaciones-string vía
    # `sys.modules[cls.__module__]` — sin registrar el módulo cargado por
    # ruta, esa búsqueda explota con `AttributeError` (`import_nexus_runs`
    # define dataclasses; `exp_r_vs_p.py`, el precedente, no).
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return cast("_ImportModule", module)


imp = _load_module()
_REPO = _find_repo_root()
_CORPUS_DIR = _REPO / "knowledge" / "islanding" / "corpus"
_MIRROR_DIR = _REPO.parent / "reto1-vanilla" / "runs" / "nexus"
_MIRROR_AVAILABLE = _MIRROR_DIR.is_dir() and any(_MIRROR_DIR.glob("*.json"))

requires_mirror = pytest.mark.skipif(
    not _MIRROR_AVAILABLE,
    reason="espejo reto1-vanilla no está montado en esta máquina (solo-lectura, fuera de este repo)",
)


class TestBitOrderAgainstTheRealCorpus:
    """Bitstrings tomados TAL CUAL de
    `runs/nexus/cr6-uniforme-p1-s0-H2-1LE.json` (espejo) — "010011" es la
    codificación msb-left directa de `asignacion_canonica`
    ([0,1,0,0,1,1] -> optimo=5); "101100" es su complemento bit-a-bit (mismo
    corte, Z2 del Max-Cut) y de hecho la muestra de MAYOR conteo real (73)
    en esa corrida — exactamente el caso que el test G6 generalizado debe
    resolver sin ambigüedad."""

    def test_dominant_sample_010011_decodes_to_the_optimum_only_under_msb_left(
        self,
    ) -> None:
        run = {
            "counts": {"010011": 66, "000000": 2},
            "stats": {"best_cut": _CR6_OPTIMO},
        }

        assert imp.dominant_bit_orders(run, _CR6_ARISTAS) == ("msb-left",)

    def test_the_z2_complement_101100_also_resolves_to_msb_left(self) -> None:
        # "101100" es el bit-flip global de "010011" (misma partición, mismo
        # corte) — real dominante (conteo 73) en cr6-uniforme-p1-s0-H2-1LE.
        run = {
            "counts": {"101100": 73, "000000": 2},
            "stats": {"best_cut": _CR6_OPTIMO},
        }

        assert imp.dominant_bit_orders(run, _CR6_ARISTAS) == ("msb-left",)

    def test_candidate_bit_orders_matches_max_cut_over_all_samples(self) -> None:
        # "000101" SOLO reproduce best_cut bajo msb-right en este grafo —
        # visto realmente en cr6-uniforme-p1-s0-H2-Emulator. Con AMBAS
        # muestras presentes, ambos ordenes quedan "consistentes" (empate
        # real de evidencia intra-corrida, no un bug).
        run = {
            "counts": {"010011": 100, "000101": 1},
            "stats": {"best_cut": _CR6_OPTIMO},
        }

        assert imp.candidate_bit_orders(run, _CR6_ARISTAS) == ("msb-left", "msb-right")
        # pero la muestra DOMINANTE ("010011", conteo 100) solo reproduce
        # best_cut bajo msb-left -> señal más fuerte, desambigua.
        assert imp.dominant_bit_orders(run, _CR6_ARISTAS) == ("msb-left",)

    def test_no_bit_order_reproduces_an_impossible_best_cut(self) -> None:
        # cr6-uniforme no tiene ningún corte de valor 6 (optimo=5, grafo de
        # 6 aristas peso 1 pero max-cut real es 5) — ningún orden debe
        # "inventar" consistencia.
        run = {"counts": {"010011": 100}, "stats": {"best_cut": 6}}

        assert imp.candidate_bit_orders(run, _CR6_ARISTAS) == ()


class TestResolveBitOrders:
    """`resolve_bit_orders` opera sobre VARIAS corridas a la vez — las que
    quedan genuinamente empatadas intra-corrida (posible en cr6/cr8 por la
    simetría Z2 + cobertura casi completa del espacio de 2^n) se desempatan
    por el consenso de las corridas SIN ambigüedad."""

    def test_unambiguous_run_resolves_without_a_tie_break(self) -> None:
        run = {"counts": {"010011": 100}, "stats": {"best_cut": _CR6_OPTIMO}}

        resolutions = imp.resolve_bit_orders([("job-a", run, _CR6_ARISTAS)])

        assert resolutions["job-a"].bit_order == "msb-left"
        assert resolutions["job-a"].reason == "unambiguous"

    def test_a_tied_run_is_broken_by_the_consensus_of_unambiguous_runs(self) -> None:
        # job-a: sin ambigüedad -> msb-left.
        run_a = {"counts": {"010011": 100}, "stats": {"best_cut": _CR6_OPTIMO}}
        # job-b: "010101" decodifica al mismo corte óptimo BAJO AMBOS
        # órdenes en este grafo (verificado: cr6-uniforme-p3-s0-H2-1LE real
        # es exactamente este caso) -> cero señal intra-corrida.
        run_b = {"counts": {"010101": 100}, "stats": {"best_cut": _CR6_OPTIMO}}
        assert imp.candidate_bit_orders(run_b, _CR6_ARISTAS) == (
            "msb-left",
            "msb-right",
        )
        assert imp.dominant_bit_orders(run_b, _CR6_ARISTAS) == ("msb-left", "msb-right")

        resolutions = imp.resolve_bit_orders(
            [("job-a", run_a, _CR6_ARISTAS), ("job-b", run_b, _CR6_ARISTAS)]
        )

        assert resolutions["job-a"].reason == "unambiguous"
        assert resolutions["job-b"].bit_order == "msb-left"
        assert resolutions["job-b"].reason == "tie_broken_by_corpus_consensus"

    def test_a_lone_tied_run_with_no_consensus_available_fails_loud(self) -> None:
        run_b = {"counts": {"010101": 100}, "stats": {"best_cut": _CR6_OPTIMO}}

        with pytest.raises(ValueError, match="empate"):
            imp.resolve_bit_orders([("job-b", run_b, _CR6_ARISTAS)])

    def test_a_run_with_no_consistent_order_fails_loud(self) -> None:
        run = {"counts": {"010011": 100}, "stats": {"best_cut": 6}}

        with pytest.raises(ValueError, match="ningún bit_order"):
            imp.resolve_bit_orders([("job-x", run, _CR6_ARISTAS)])


@requires_mirror
class TestImportOnTheMirror:
    """El importador real sobre las 19 corridas del espejo `reto1-vanilla`."""

    def test_imports_exactly_nineteen_runs(self, tmp_path: Path) -> None:
        summary = imp.run_import(_MIRROR_DIR, _CORPUS_DIR, tmp_path / "out")

        assert len(summary.results) == 19

    def test_every_run_resolves_to_msb_left_empirically(self, tmp_path: Path) -> None:
        # Confirmado a mano contra las 19 corridas reales (ver reporte de la
        # tarea): msb-left es el único orden que nunca se contradice, y el
        # único ganador único en las corridas con señal inequívoca
        # (incluyendo ieee14-flujo, sin la simetría Z2 de cr6/cr8).
        summary = imp.run_import(_MIRROR_DIR, _CORPUS_DIR, tmp_path / "out")

        bit_orders = {r.bit_order for r in summary.results}
        assert bit_orders == {"msb-left"}

    def test_exactly_four_consensus_predicates_with_two_legs_each(
        self, tmp_path: Path
    ) -> None:
        # cr6-uniforme p1, cr8-uniforme p1/p2/p3 — cada uno corrido en
        # H2-1LE y H2-Emulator.
        summary = imp.run_import(_MIRROR_DIR, _CORPUS_DIR, tmp_path / "out")

        assert len(summary.consensus) == 4
        pairs = {(entry["instance"], entry["p"]) for entry in summary.consensus}
        assert pairs == {
            ("cr6-uniforme", 1),
            ("cr8-uniforme", 1),
            ("cr8-uniforme", 2),
            ("cr8-uniforme", 3),
        }
        for entry in summary.consensus:
            assert len(entry["predicate"]["legs"]) == 2
            assert entry["predicate"]["agreement"] is True

    def test_the_import_is_byte_identical_across_two_independent_runs(
        self, tmp_path: Path
    ) -> None:
        out_a = tmp_path / "a"
        out_b = tmp_path / "b"

        imp.run_import(_MIRROR_DIR, _CORPUS_DIR, out_a)
        imp.run_import(_MIRROR_DIR, _CORPUS_DIR, out_b)

        files_a = sorted(p.relative_to(out_a) for p in out_a.rglob("*.json"))
        files_b = sorted(p.relative_to(out_b) for p in out_b.rglob("*.json"))
        assert files_a == files_b
        for rel in files_a:
            assert (out_a / rel).read_bytes() == (out_b / rel).read_bytes()

    def test_index_json_carries_one_entry_per_run_with_the_wire_event_shape(
        self, tmp_path: Path
    ) -> None:
        out_dir = tmp_path / "out"
        imp.run_import(_MIRROR_DIR, _CORPUS_DIR, out_dir)

        index = json.loads((out_dir / "index.json").read_text())
        assert len(index["imports"]) == 19
        first = index["imports"][0]
        event = first["event"]
        assert set(event) == {
            "job_id",
            "backend_id",
            "statement_digest",
            "raw_blob_digest",
            "normalized_digest",
            "imported_by",
            "imported_at",
        }
