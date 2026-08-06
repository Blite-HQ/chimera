"""Unit tests de `ExactEvolve._invoke_impl` (diagonalización dispersa,
`scipy.sparse.linalg.expm_multiply`) — ancla FORMAL_EXACT del contrato
Contrato-3 (docs/specs/generalidad-retos.md), lado independiente del
circuito (`capabilities/quantum/tests/test_trotter_evolve.py` es la
integración que compara ambos — ver knowledge/quantum/11-receta-c3-tfim-trotter.md).

Operador de referencia (construido AQUÍ, no en el manifest — ADR-029): cadena
abierta de N sitios, acoplamiento ZZ a vecinos con coeficiente -1.0 y campo X
local con coeficiente -h por sitio. Los números dorados de este archivo se
computaron en vivo (venv del repo, 2026-07-31/08-01) contra este mismo
operador — ver knowledge/quantum/11 §4.2/§6.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip(
    "scipy", reason="extra opcional: uv sync --all-packages --extra full"
)

from blite_cap_numeric import ExactEvolve  # noqa: E402

_TOLERANCE = 1e-6


def _chain_terms(n: int, h: float) -> list[dict[str, Any]]:
    """Términos ZZ(vecino, coef -1.0) + X(local, coef -h) — cadena abierta."""
    terms: list[dict[str, Any]] = []
    for i in range(n - 1):
        pauli = ["I"] * n
        pauli[i] = "Z"
        pauli[i + 1] = "Z"
        terms.append({"pauli": "".join(pauli), "coefficient": -1.0})
    for i in range(n):
        pauli = ["I"] * n
        pauli[i] = "X"
        terms.append({"pauli": "".join(pauli), "coefficient": -h})
    return terms


def _z_observables(n: int) -> list[dict[str, str]]:
    observables: list[dict[str, str]] = []
    for i in range(n):
        pauli = ["I"] * n
        pauli[i] = "Z"
        observables.append({"label": f"Z{i}", "pauli": "".join(pauli)})
    return observables


def _zz_observables(n: int) -> list[dict[str, str]]:
    observables: list[dict[str, str]] = []
    for i in range(n - 1):
        pauli = ["I"] * n
        pauli[i] = "Z"
        pauli[i + 1] = "Z"
        observables.append({"label": f"ZZ{i}", "pauli": "".join(pauli)})
    return observables


def _invoke(n: int, h: float, time: float) -> dict[str, Any]:
    return ExactEvolve().invoke(
        {
            "n_sites": n,
            "terms": _chain_terms(n, h),
            "time": time,
            "observables": _z_observables(n) + _zz_observables(n),
        }
    )


def _values_by_label(result: dict[str, Any], prefix: str) -> list[float]:
    return [
        e["value"]
        for e in result["expectations"]
        if e["label"].startswith(prefix) and e["label"][len(prefix) :].isdigit()
    ]


class TestGoldenValues:
    """N=8, t=1.0 — tabla congelada en knowledge/quantum/11 §4.2 (tolerancia 1e-6)."""

    @pytest.mark.parametrize(
        ("h", "expected_z0", "expected_z0z1"),
        [
            (0.5, 0.672315, 0.655737),
            (1.0, -0.033022, 0.434251),
            (2.0, -0.436532, 0.479051),
        ],
    )
    def test_z0_and_z0z1_match_golden_table(
        self, h: float, expected_z0: float, expected_z0z1: float
    ) -> None:
        result = _invoke(8, h, 1.0)
        by_label = {e["label"]: e["value"] for e in result["expectations"]}

        assert by_label["Z0"] == pytest.approx(expected_z0, abs=_TOLERANCE)
        assert by_label["ZZ0"] == pytest.approx(expected_z0z1, abs=_TOLERANCE)

    def test_max_abs_z_at_h_0_5_matches_golden(self) -> None:
        result = _invoke(8, 0.5, 1.0)
        z_values = _values_by_label(result, "Z")

        assert max(abs(v) for v in z_values) == pytest.approx(0.868053, abs=_TOLERANCE)

    @pytest.mark.parametrize("n", [6, 12])
    def test_light_cone_z0_matches_across_sizes(self, n: int) -> None:
        """Lieb-Robinson (recipe §5.3): a t=1 el borde no distingue N=6 de
        N=12 — ⟨Z0⟩ debe coincidir con N=8 a 6 cifras. N=12 es rápido
        (~0.1s medido) — se corre en un solo test, no en toda la malla."""
        result = _invoke(n, 0.5, 1.0)
        by_label = {e["label"]: e["value"] for e in result["expectations"]}

        assert by_label["Z0"] == pytest.approx(0.672315, abs=_TOLERANCE)

    def test_norm_is_preserved(self) -> None:
        result = _invoke(8, 1.0, 1.0)

        assert result["norm"] == pytest.approx(1.0, abs=1e-9)

    def test_method_and_backend_are_reported(self) -> None:
        result = _invoke(8, 1.0, 1.0)

        assert result["method"] == "expm_multiply"
        assert result["backend"].startswith("scipy-")


class TestInputValidation:
    def test_missing_n_sites_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="n_sites"):
            ExactEvolve().invoke(
                {
                    "terms": _chain_terms(2, 1.0),
                    "time": 1.0,
                    "observables": _z_observables(2),
                }
            )

    def test_non_integer_n_sites_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="n_sites"):
            ExactEvolve().invoke(
                {
                    "n_sites": "2",
                    "terms": _chain_terms(2, 1.0),
                    "time": 1.0,
                    "observables": _z_observables(2),
                }
            )

    def test_boolean_n_sites_raises_value_error(self) -> None:
        # bool es subclase de int: True se colaría como n_sites=1
        with pytest.raises(ValueError, match="n_sites"):
            ExactEvolve().invoke(
                {
                    "n_sites": True,
                    "terms": _chain_terms(2, 1.0),
                    "time": 1.0,
                    "observables": _z_observables(2),
                }
            )

    def test_n_sites_out_of_range_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="n_sites"):
            ExactEvolve().invoke(
                {
                    "n_sites": 15,
                    "terms": _chain_terms(2, 1.0),
                    "time": 1.0,
                    "observables": _z_observables(2),
                }
            )

    def test_missing_terms_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="terms"):
            ExactEvolve().invoke(
                {"n_sites": 2, "time": 1.0, "observables": _z_observables(2)}
            )

    def test_empty_terms_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="terms"):
            ExactEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": [],
                    "time": 1.0,
                    "observables": _z_observables(2),
                }
            )

    def test_term_pauli_wrong_length_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="pauli"):
            ExactEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": [{"pauli": "X", "coefficient": 1.0}],
                    "time": 1.0,
                    "observables": _z_observables(2),
                }
            )

    def test_term_pauli_invalid_alphabet_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="pauli"):
            ExactEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": [{"pauli": "XW", "coefficient": 1.0}],
                    "time": 1.0,
                    "observables": _z_observables(2),
                }
            )

    def test_term_non_numeric_coefficient_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="coefficient"):
            ExactEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": [{"pauli": "XI", "coefficient": "1.0"}],
                    "time": 1.0,
                    "observables": _z_observables(2),
                }
            )

    def test_term_boolean_coefficient_raises_value_error(self) -> None:
        # bool es subclase de int: True se colaría como coefficient=1
        with pytest.raises(ValueError, match="coefficient"):
            ExactEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": [{"pauli": "XI", "coefficient": True}],
                    "time": 1.0,
                    "observables": _z_observables(2),
                }
            )

    def test_non_numeric_time_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="time"):
            ExactEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": _chain_terms(2, 1.0),
                    "time": "1.0",
                    "observables": _z_observables(2),
                }
            )

    def test_initial_bitstring_wrong_length_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="initial_bitstring"):
            ExactEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": _chain_terms(2, 1.0),
                    "time": 1.0,
                    "initial_bitstring": "0",
                    "observables": _z_observables(2),
                }
            )

    def test_initial_bitstring_invalid_alphabet_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="initial_bitstring"):
            ExactEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": _chain_terms(2, 1.0),
                    "time": 1.0,
                    "initial_bitstring": "02",
                    "observables": _z_observables(2),
                }
            )

    def test_missing_observables_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="observables"):
            ExactEvolve().invoke(
                {"n_sites": 2, "terms": _chain_terms(2, 1.0), "time": 1.0}
            )

    def test_empty_observables_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="observables"):
            ExactEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": _chain_terms(2, 1.0),
                    "time": 1.0,
                    "observables": [],
                }
            )

    def test_observable_missing_label_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="label"):
            ExactEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": _chain_terms(2, 1.0),
                    "time": 1.0,
                    "observables": [{"pauli": "ZI"}],
                }
            )


class TestGenericitySelfCheck:
    """ADR-029: el gate del repo lee entry points INSTALADOS y no verá esta
    capability hasta un reinstall — esta aserción local es la que cubre en
    vivo (ver tests/invariants/test_capability_genericity.py)."""

    def test_manifest_has_no_scenario_vocabulary(self) -> None:
        denylist_path = (
            Path(__file__).resolve().parents[3]
            / "tests"
            / "invariants"
            / "scenario_denylist.txt"
        )
        denylist = [
            line.strip().lower()
            for line in denylist_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]

        manifest = ExactEvolve().manifest
        text = json.dumps(dataclasses.asdict(manifest), default=str).lower()

        violations = [term for term in denylist if term in text]
        assert not violations, (
            f"manifest contiene vocabulario de escenario: {violations}"
        )
