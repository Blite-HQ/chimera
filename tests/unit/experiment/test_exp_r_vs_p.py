"""Tests de INVARIANTES para `scripts/exp_r_vs_p.py` (Task 4 — r vs p).

Deliberadamente NO congela valores "golden" de QAOA: Qiskit/Aer no es
bit-determinista entre versiones (misma lección que Task 1, ver
`.superpowers/sdd/task4-brief.md`). Lo que se testea son invariantes que
cualquier corrida válida debe cumplir (r∈[0,1], cpsat.r==1.0 sobre el
óptimo congelado, determinismo DENTRO de la corrida) — no el valor exacto
de energía/partición que QAOA devuelva.

`scripts/` no es un paquete instalable (no está en `tool.uv.workspace` ni
en el `include` de pyright — ver pyproject.toml), así que el módulo se
carga por ruta con `importlib.util.spec_from_file_location` y se envuelve
tras un `Protocol` tipado (`_ExpModule`) para que pyright, que SÍ cubre
`tests/` en modo strict, tenga tipos concretos en cada atributo en vez de
`Any` implícito.

Instancia MINÚSCULA para el barrido QAOA (mantener los tests rápidos):
triángulo de 3 nodos con aristas w01=1, w12=2, w02=3 — el mismo QUBO
`_G6` de `capabilities/solvers/tests/test_qubo_solver.py` (óptimo 5),
construido con el transform canónico de context.md § Grafo↔QUBO.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Protocol, cast

import pytest

# Triángulo w01=1, w12=2, w02=3 -> QUBO por el transform canónico:
#   matrix[0][0]=1+3=4  matrix[1][1]=1+2=3  matrix[2][2]=3+2=5
#   matrix[0][1]=-1     matrix[0][2]=-3     matrix[1][2]=-2
# Óptimo de corte = 5 (mismo caso hand-checked que `_G6` en solvers).
_TRIANGLE_MATRIX: list[list[int]] = [[4, -1, -3], [-1, 3, -2], [-3, -2, 5]]
_TRIANGLE_OPTIMO = 5


class _ExpModule(Protocol):
    """Firma tipada de las funciones puras/orquestación de exp_r_vs_p.py."""

    def compute_ratio(self, energy: float, optimo: float) -> float: ...

    def summarize(self, ratios: list[float]) -> dict[str, float | int]: ...

    def load_instance(
        self, name: str
    ) -> tuple[list[list[int]], int, dict[str, Any]]: ...

    def run_baselines(
        self, matrix: list[list[int]], optimo: int
    ) -> dict[str, dict[str, Any]]: ...

    def run_qaoa_sweep(
        self,
        matrix: list[list[int]],
        optimo: int,
        p_values: list[int],
        seeds: list[int],
    ) -> dict[int, dict[str, Any]]: ...

    def build_report(
        self,
        instance: str,
        optimo: int,
        config: dict[str, Any],
        qaoa: dict[int, dict[str, Any]],
        baselines: dict[str, dict[str, Any]],
    ) -> dict[str, Any]: ...


def _find_script() -> Path:
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        candidate = base / "scripts" / "exp_r_vs_p.py"
        if candidate.is_file():
            return candidate
    msg = "scripts/exp_r_vs_p.py no encontrado sobre este archivo"
    raise FileNotFoundError(msg)


def _load_module() -> _ExpModule:
    script_path = _find_script()
    spec = importlib.util.spec_from_file_location("exp_r_vs_p", script_path)
    if spec is None:
        msg = f"no se pudo construir un spec de import para {script_path}"
        raise ImportError(msg)
    loader = spec.loader
    if loader is None:
        msg = f"el spec de {script_path} no tiene loader"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return cast(_ExpModule, module)


exp = _load_module()


class TestComputeRatio:
    def test_ratio_is_energy_over_optimo(self) -> None:
        assert exp.compute_ratio(30, 60) == 0.5

    def test_ratio_at_optimum_is_one(self) -> None:
        assert exp.compute_ratio(21692, 21692) == 1.0

    def test_ratio_can_exceed_zero_below_optimum(self) -> None:
        assert exp.compute_ratio(0, 60) == 0.0


class TestSummarize:
    def test_mean_std_n_min_max_on_three_values(self) -> None:
        stats = exp.summarize([1.0, 2.0, 3.0])

        assert stats["n"] == 3
        assert stats["mean"] == 2.0
        assert stats["min"] == 1.0
        assert stats["max"] == 3.0
        # Poblacional (ddof=0): sqrt(mean((x-mean)^2)) = sqrt(2/3)
        assert stats["std"] == pytest.approx((2.0 / 3.0) ** 0.5)

    def test_single_value_has_zero_std(self) -> None:
        # n=1 debe seguir siendo válido (barrido con seeds=[1]) — población,
        # no muestral, para que no explote con n=1 (ddof=1 dividiría por 0).
        stats = exp.summarize([0.75])

        assert stats == {"mean": 0.75, "std": 0.0, "n": 1, "min": 0.75, "max": 0.75}


class TestLoadInstance:
    def test_ieee6_flujo_matches_frozen_optimum(self) -> None:
        matrix, optimo, meta = exp.load_instance("ieee6-flujo")

        assert optimo == 21692
        assert len(matrix) == 6
        assert meta["n_nodos"] == 6


class TestRunBaselines:
    """Corridas rápidas (CP-SAT/greedy/GW sobre 6 nodos, <2s)."""

    def test_cpsat_reaches_the_frozen_optimum(self) -> None:
        matrix, optimo, _ = exp.load_instance("ieee6-flujo")

        baselines = exp.run_baselines(matrix, optimo)

        assert baselines["cpsat"]["r"] == 1.0

    def test_gw_and_greedy_ratios_are_within_unit_interval(self) -> None:
        matrix, optimo, _ = exp.load_instance("ieee6-flujo")

        baselines = exp.run_baselines(matrix, optimo)

        assert 0.0 <= baselines["gw"]["r"] <= 1.0
        assert 0.0 <= baselines["greedy"]["r"] <= 1.0

    def test_energies_are_consistent_with_their_ratios(self) -> None:
        matrix, optimo, _ = exp.load_instance("ieee6-flujo")

        baselines = exp.run_baselines(matrix, optimo)

        for name in ("gw", "greedy", "cpsat"):
            assert baselines[name]["energy"] == pytest.approx(
                baselines[name]["r"] * optimo
            )

    def test_run_baselines_is_deterministic(self) -> None:
        matrix, optimo, _ = exp.load_instance("ieee6-flujo")

        first = exp.run_baselines(matrix, optimo)
        second = exp.run_baselines(matrix, optimo)

        assert first == second


class TestRunQaoaSweep:
    """Instancia MINÚSCULA (triángulo 3 nodos), p_values=[1], seeds=[1].

    Fix 4b (task4b-brief.md): `run_qaoa_sweep` ya no reporta solo el ratio
    best-of-samples (trivialmente 1.0 en instancias chicas — artefacto de
    muestreo, NO una métrica de benchmarking válida). Reporta:
      - `r_esperado` — stats (mean/std/n/min/max) del ratio del valor
        esperado EXACTO ⟨C⟩ (`expected_energy`) sobre las semillas — curva
        primaria, casi determinista en p (ver `_G6`/task4b-brief.md).
      - `r_muestral` — stats del ratio muestral (`sampled_mean_energy`)
        sobre las semillas — refleja ruido de muestreo, honesto sobre
        n≥5 semillas.
      - `success_rate` — fracción de semillas cuyo best-of-samples alcanza
        el óptimo (dato secundario, NO la curva r).
    """

    def test_structure_and_ratio_bounds(self) -> None:
        sweep = exp.run_qaoa_sweep(
            _TRIANGLE_MATRIX, _TRIANGLE_OPTIMO, p_values=[1], seeds=[1]
        )

        assert set(sweep.keys()) == {1}
        entry = sweep[1]
        assert set(entry.keys()) == {
            "best_energies",
            "expected_energies",
            "sampled_mean_energies",
            "best_ratios",
            "r_esperado",
            "r_muestral",
            "success_rate",
        }
        assert len(entry["best_energies"]) == 1
        assert len(entry["expected_energies"]) == 1
        assert len(entry["sampled_mean_energies"]) == 1
        assert len(entry["best_ratios"]) == 1
        assert 0.0 <= entry["best_ratios"][0] <= 1.0
        assert entry["r_esperado"]["n"] == 1
        assert 0.0 <= entry["r_esperado"]["mean"] <= 1.0
        assert entry["r_muestral"]["n"] == 1
        assert 0.0 <= entry["r_muestral"]["mean"] <= 1.0
        assert 0.0 <= entry["success_rate"] <= 1.0

    def test_expected_energy_does_not_exceed_optimum(self) -> None:
        # expected_energy es una combinación convexa de energías de bitstring
        # (todas en [0, optimo] para Max-Cut) ⇒ r_esperado ∈ [0,1] SIEMPRE,
        # no solo empíricamente.
        sweep = exp.run_qaoa_sweep(
            _TRIANGLE_MATRIX, _TRIANGLE_OPTIMO, p_values=[1, 2], seeds=[1]
        )

        for p in (1, 2):
            for energy in sweep[p]["expected_energies"]:
                assert 0.0 <= energy <= _TRIANGLE_OPTIMO

    def test_same_seed_is_deterministic_within_the_run(self) -> None:
        first = exp.run_qaoa_sweep(
            _TRIANGLE_MATRIX, _TRIANGLE_OPTIMO, p_values=[1], seeds=[1]
        )
        second = exp.run_qaoa_sweep(
            _TRIANGLE_MATRIX, _TRIANGLE_OPTIMO, p_values=[1], seeds=[1]
        )

        assert first[1]["best_ratios"] == second[1]["best_ratios"]
        assert first[1]["expected_energies"] == second[1]["expected_energies"]
        assert first[1]["sampled_mean_energies"] == second[1]["sampled_mean_energies"]
        assert first[1]["r_esperado"] == second[1]["r_esperado"]
        assert first[1]["r_muestral"] == second[1]["r_muestral"]


class TestBuildReport:
    def test_schema_has_the_expected_keys(self) -> None:
        config: dict[str, Any] = {"p_values": [1], "seeds": [1]}
        qaoa: dict[int, dict[str, Any]] = {
            1: {
                "ratios": [1.0],
                "energies": [5.0],
                "mean": 1.0,
                "std": 0.0,
                "n": 1,
                "best": 1.0,
            }
        }
        baselines: dict[str, dict[str, Any]] = {
            "gw": {"energy": 5.0, "r": 1.0},
            "greedy": {"energy": 5.0, "r": 1.0},
            "cpsat": {"energy": 5.0, "r": 1.0},
        }

        report = exp.build_report("triangle", 5, config, qaoa, baselines)

        assert report["instance"] == "triangle"
        assert report["optimo"] == 5
        assert report["config"] == config
        assert report["qaoa"] == qaoa
        assert report["baselines"] == baselines
