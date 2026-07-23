"""Integración del demo (freeze §15.5 + carril 2b): ieee14 de punta a punta.

QAOA (Aer + seed) propone una partición BUENA sobre ieee14-flujo; la falla
sembrada (bus 1 vía `capabilities_sim_api`) queda estrictamente por debajo —
la narrativa del demo es exactamente esa brecha. Los dos lados se recomputan
por doble vía (energía QUBO == corte sobre aristas) antes de compararse.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip(
    "qiskit", reason="extra opcional: uv sync --all-packages --extra qaoa"
)

from blite_cap_quantum import QaoaSolver  # noqa: E402
from capabilities_sim_api import recompute_seeded_failure  # noqa: E402

_FROZEN_OPTIMUM = 57_070
_SEEDED_RATIO = 0.5712


def _find_corpus() -> Path:
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        candidate = base / "knowledge" / "islanding" / "corpus"
        if candidate.is_dir():
            return candidate
    msg = "corpus de islanding no encontrado sobre este archivo"
    raise FileNotFoundError(msg)


def test_qaoa_good_partition_beats_the_seeded_bad_one_on_ieee14() -> None:
    # Arrange — Q por la regla quantum/02 §1.2 desde el corpus congelado
    record: dict[str, Any] = json.loads(
        (_find_corpus() / "ieee14-flujo.json").read_text(encoding="utf-8")
    )
    edges = [(int(u), int(v), int(w)) for u, v, w in record["aristas"]]
    n = int(record["n_nodos"])
    matrix = [[0] * n for _ in range(n)]
    for u, v, w in edges:
        matrix[u][u] += w
        matrix[v][v] += w
        matrix[u][v] -= w
        matrix[v][u] -= w

    # Act — la propuesta cuántica y la falla sembrada
    proposed = QaoaSolver().invoke(
        {"matrix": matrix, "layers": 2, "seed": 1, "reference_optimum": _FROZEN_OPTIMUM}
    )
    seeded = recompute_seeded_failure(instance="ieee14-flujo", bus=1)

    # Assert — doble vía de la propuesta: energía QUBO == corte sobre aristas
    cut = sum(
        w for u, v, w in edges if proposed["assignment"][u] != proposed["assignment"][v]
    )
    assert cut == proposed["energy"]

    # La brecha que sostiene el guion: buena > sembrada (0.5712, congelada)
    assert round(seeded.r, 4) == _SEEDED_RATIO
    assert proposed["approximation_ratio"] > seeded.r
