"""Unit tests de `TrotterEvolve._invoke_impl` (Qiskit `PauliEvolutionGate` +
`Statevector`, Lie-Trotter/Suzuki) — proponente por circuito del contrato
Contrato-3 (docs/specs/generalidad-retos.md), lado independiente del ancla
exacta (`capabilities/numeric/tests/test_exact_evolve.py`; este archivo SÍ
importa ambas capabilities para la comparación cruzada — es la integración
prevista por el contrato, no una violación de independencia de módulos de
producción).

Operador de referencia (construido AQUÍ, no en el manifest — ADR-029): cadena
abierta de N sitios, acoplamiento ZZ a vecinos con coeficiente -1.0 y campo X
local con coeficiente -h por sitio. Los números dorados se computaron en vivo
(venv del repo, 2026-07-31/08-01) — ver
knowledge/quantum/11-receta-c3-tfim-trotter.md §4.1 (definición del error
relativo), §4.2 (malla r=16), §4.3 (control negativo r=2), §1.5 (por qué la
razón de convergencia ≈4 NO prueba orden 2 aquí).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip(
    "qiskit", reason="extra opcional: uv sync --all-packages --extra qaoa"
)

from blite_cap_numeric import ExactEvolve  # noqa: E402
from blite_cap_quantum import TrotterEvolve  # noqa: E402

_TOLERANCE = 2e-4


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
    return [
        {"label": f"Z{i}", "pauli": "".join("Z" if j == i else "I" for j in range(n))}
        for i in range(n)
    ]


def _zz_observables(n: int) -> list[dict[str, str]]:
    return [
        {
            "label": f"ZZ{i}",
            "pauli": "".join("Z" if j in (i, i + 1) else "I" for j in range(n)),
        }
        for i in range(n - 1)
    ]


def _rel_error(candidate: list[float], reference: list[float]) -> float:
    """Error relativo L-infinito (recipe §4.1): normalizado por la escala de
    la serie de referencia, no por elemento (indefinido donde cruza cero)."""
    denom = max(max(abs(r) for r in reference), 1e-12)
    return max(abs(c - r) for c, r in zip(candidate, reference, strict=True)) / denom


def _exact_series(n: int, h: float, time: float) -> tuple[list[float], list[float]]:
    result = ExactEvolve().invoke(
        {
            "n_sites": n,
            "terms": _chain_terms(n, h),
            "time": time,
            "observables": _z_observables(n) + _zz_observables(n),
        }
    )
    by_label = {e["label"]: e["value"] for e in result["expectations"]}
    z = [by_label[f"Z{i}"] for i in range(n)]
    zz = [by_label[f"ZZ{i}"] for i in range(n - 1)]
    return z, zz


def _trotter_series(
    n: int, h: float, time: float, steps: int, order: int = 1
) -> tuple[list[float], list[float], dict[str, Any]]:
    result = TrotterEvolve().invoke(
        {
            "n_sites": n,
            "terms": _chain_terms(n, h),
            "time": time,
            "observables": _z_observables(n) + _zz_observables(n),
            "steps": steps,
            "order": order,
        }
    )
    by_label = {e["label"]: e["value"] for e in result["expectations"]}
    z = [by_label[f"Z{i}"] for i in range(n)]
    zz = [by_label[f"ZZ{i}"] for i in range(n - 1)]
    return z, zz, result


class TestGoldenErrorsVsExact:
    """N=8, t=1.0, order=1 — tabla congelada knowledge/quantum/11 §4.2/§4.3."""

    @pytest.mark.parametrize(
        ("h", "steps", "expected_err_z", "expected_err_zz"),
        [
            (0.5, 16, 0.00060, 0.00102),
            (1.0, 16, 0.00442, 0.00321),
            (2.0, 16, 0.00903, 0.00496),
            (0.5, 2, 0.04569, 0.07867),
            (1.0, 2, 0.32550, 0.23746),
            (2.0, 2, 1.03393, 0.40682),
        ],
    )
    def test_relative_error_matches_golden_table(
        self, h: float, steps: int, expected_err_z: float, expected_err_zz: float
    ) -> None:
        z_ref, zz_ref = _exact_series(8, h, 1.0)
        z_cand, zz_cand, _ = _trotter_series(8, h, 1.0, steps)

        err_z = _rel_error(z_cand, z_ref)
        err_zz = _rel_error(zz_cand, zz_ref)

        assert err_z == pytest.approx(expected_err_z, abs=_TOLERANCE)
        assert err_zz == pytest.approx(expected_err_zz, abs=_TOLERANCE)


class TestControlNegativo:
    def test_control_negativo_dt_grande_diverge(self) -> None:
        """recipe §4.3: con dt grande (steps=2) el proponente debe FALLAR el
        criterio oficial (5%) en al menos una serie, en los tres puntos del
        barrido — y en h=0.5 (el punto más ordenado) es la serie ⟨ZᵢZᵢ₊₁⟩ la
        que lo caza, NO la serie ⟨Zᵢ⟩ (que pasaría sola, dando un falso
        'pass' si solo se verificara una serie).

        Por qué existe este test (recipe §4.3, S-C §3): un error 0.0000 con
        dt grande contra la ED sería sospecha de código compartido entre el
        proponente (circuito) y el ancla (diagonalización exacta) — no un
        hallazgo. Este test caza exactamente esa regresión.
        """
        tolerance = 0.05
        for h in (0.5, 1.0, 2.0):
            z_ref, zz_ref = _exact_series(8, h, 1.0)
            z_cand, zz_cand, _ = _trotter_series(8, h, 1.0, steps=2)
            err_z = _rel_error(z_cand, z_ref)
            err_zz = _rel_error(zz_cand, zz_ref)

            assert err_z > tolerance or err_zz > tolerance, (
                f"h={h}: ninguna serie superó el criterio del 5% con steps=2 "
                f"(err_z={err_z}, err_zz={err_zz}) — sospecha de código compartido"
            )
            if h == 0.5:
                assert err_z <= tolerance, "err_z debería SEGUIR pasando en h=0.5"
                assert err_zz > tolerance, "err_zz es la serie que caza h=0.5"


class TestConvergencia:
    def test_convergencia_es_orden_dt_cuadrado(self) -> None:
        """err(steps=8)/err(steps=16) ≈ 4 en este montaje (h=1.0).

        Esto NO prueba que la fórmula de Lie-Trotter (orden 1) sea de orden
        2 en general (recipe §1.5): aquí ocurre por una cancelación de
        simetría específica de este Hamiltoniano (real, simétrico en la
        base Z) y este estado inicial real — no porque el orden 1 sea
        genéricamente O(dt²). El test registra la razón medida, no una
        propiedad universal del método.
        """
        h = 1.0
        z_ref, _ = _exact_series(8, h, 1.0)
        z8, _, _ = _trotter_series(8, h, 1.0, steps=8)
        z16, _, _ = _trotter_series(8, h, 1.0, steps=16)

        err8 = _rel_error(z8, z_ref)
        err16 = _rel_error(z16, z_ref)
        ratio = err8 / err16

        assert 3.6 <= ratio <= 4.4


class TestProperties:
    def test_norm_is_preserved(self) -> None:
        _, _, result = _trotter_series(8, 1.0, 1.0, steps=16)

        assert result["norm"] == pytest.approx(1.0, abs=1e-9)

    def test_expectations_are_within_bounds(self) -> None:
        _, _, result = _trotter_series(8, 1.0, 1.0, steps=16)

        for expectation in result["expectations"]:
            assert -1.0 <= expectation["value"] <= 1.0

    def test_time_zero_reproduces_initial_condition(self) -> None:
        z, zz, result = _trotter_series(8, 1.0, 0.0, steps=16)

        assert all(v == pytest.approx(1.0, abs=1e-9) for v in z)
        assert all(v == pytest.approx(1.0, abs=1e-9) for v in zz)
        assert result["norm"] == pytest.approx(1.0, abs=1e-9)


class TestDeterminism:
    def test_identical_invocations_return_identical_dicts(self) -> None:
        payload = {
            "n_sites": 8,
            "terms": _chain_terms(8, 1.0),
            "time": 1.0,
            "observables": _z_observables(8) + _zz_observables(8),
            "steps": 16,
            "order": 1,
        }

        first = TrotterEvolve().invoke(payload)
        second = TrotterEvolve().invoke(payload)

        assert first == second


class TestEndianness:
    def test_asymmetric_operator_distinguishes_sites(self) -> None:
        """Pin de la reversión de label (`label[::-1]`).

        Un `initial_bitstring` SIMÉTRICO ('00') no sirve para este test: la
        reversión global de todos los strings de Pauli (términos +
        observables) es una simetría del problema (cadena abierta invertida
        sigue siendo una cadena abierta) y el resultado numérico es
        IDÉNTICO con o sin reversión — verificado en vivo antes de escribir
        este test. Con `initial_bitstring='01'` (asimétrico) esa simetría se
        rompe: la preparación de estado coloca cada bit en su qubit por
        ÍNDICE DIRECTO (sin reversión), así que si el operador/observable
        pierde la reversión, el sitio evolucionado deja de coincidir con el
        qubit leído por el observable — y el valor SÍ cambia. Confirmado
        empíricamente: con la reversión, Z0=-0.416/Z1=-1.0; sin ella,
        Z0=+0.416/Z1=+1.0 — un test que no distinguiera esto sería inútil.
        """
        payload = {
            "n_sites": 2,
            "terms": [{"pauli": "XI", "coefficient": 1.0}],
            "time": 1.0,
            "initial_bitstring": "01",
            "observables": [
                {"label": "Z0", "pauli": "ZI"},
                {"label": "Z1", "pauli": "IZ"},
            ],
        }

        trotter = TrotterEvolve().invoke({**payload, "steps": 16})
        exact = ExactEvolve().invoke(payload)

        trotter_values = {e["label"]: e["value"] for e in trotter["expectations"]}
        exact_values = {e["label"]: e["value"] for e in exact["expectations"]}

        assert abs(trotter_values["Z0"] - trotter_values["Z1"]) > 0.5
        assert trotter_values["Z0"] == pytest.approx(exact_values["Z0"], abs=1e-3)
        assert trotter_values["Z1"] == pytest.approx(exact_values["Z1"], abs=1e-3)
        assert trotter_values["Z1"] == pytest.approx(-1.0, abs=1e-6)


class TestInputValidation:
    def test_missing_n_sites_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="n_sites"):
            TrotterEvolve().invoke(
                {"terms": _chain_terms(2, 1.0), "time": 1.0, "observables": _z_observables(2)}
            )

    def test_non_integer_n_sites_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="n_sites"):
            TrotterEvolve().invoke(
                {"n_sites": "2", "terms": _chain_terms(2, 1.0), "time": 1.0, "observables": _z_observables(2)}
            )

    def test_boolean_n_sites_raises_value_error(self) -> None:
        # bool es subclase de int: True se colaría como n_sites=1
        with pytest.raises(ValueError, match="n_sites"):
            TrotterEvolve().invoke(
                {"n_sites": True, "terms": _chain_terms(2, 1.0), "time": 1.0, "observables": _z_observables(2)}
            )

    def test_n_sites_out_of_range_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="n_sites"):
            TrotterEvolve().invoke(
                {"n_sites": 0, "terms": _chain_terms(2, 1.0), "time": 1.0, "observables": _z_observables(2)}
            )

    def test_empty_terms_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="terms"):
            TrotterEvolve().invoke(
                {"n_sites": 2, "terms": [], "time": 1.0, "observables": _z_observables(2)}
            )

    def test_term_pauli_invalid_alphabet_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="pauli"):
            TrotterEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": [{"pauli": "XW", "coefficient": 1.0}],
                    "time": 1.0,
                    "observables": _z_observables(2),
                }
            )

    def test_term_non_numeric_coefficient_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="coefficient"):
            TrotterEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": [{"pauli": "XI", "coefficient": "1.0"}],
                    "time": 1.0,
                    "observables": _z_observables(2),
                }
            )

    def test_term_boolean_coefficient_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="coefficient"):
            TrotterEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": [{"pauli": "XI", "coefficient": True}],
                    "time": 1.0,
                    "observables": _z_observables(2),
                }
            )

    def test_non_numeric_time_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="time"):
            TrotterEvolve().invoke(
                {"n_sites": 2, "terms": _chain_terms(2, 1.0), "time": "1.0", "observables": _z_observables(2)}
            )

    def test_initial_bitstring_wrong_length_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="initial_bitstring"):
            TrotterEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": _chain_terms(2, 1.0),
                    "time": 1.0,
                    "initial_bitstring": "0",
                    "observables": _z_observables(2),
                }
            )

    def test_empty_observables_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="observables"):
            TrotterEvolve().invoke(
                {"n_sites": 2, "terms": _chain_terms(2, 1.0), "time": 1.0, "observables": []}
            )

    def test_observable_missing_label_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="label"):
            TrotterEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": _chain_terms(2, 1.0),
                    "time": 1.0,
                    "observables": [{"pauli": "ZI"}],
                }
            )

    def test_steps_below_one_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="steps"):
            TrotterEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": _chain_terms(2, 1.0),
                    "time": 1.0,
                    "observables": _z_observables(2),
                    "steps": 0,
                }
            )

    def test_boolean_steps_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="steps"):
            TrotterEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": _chain_terms(2, 1.0),
                    "time": 1.0,
                    "observables": _z_observables(2),
                    "steps": True,
                }
            )

    def test_invalid_order_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="order"):
            TrotterEvolve().invoke(
                {
                    "n_sites": 2,
                    "terms": _chain_terms(2, 1.0),
                    "time": 1.0,
                    "observables": _z_observables(2),
                    "order": 3,
                }
            )


class TestGenericitySelfCheck:
    """ADR-029: el gate del repo lee entry points INSTALADOS y no verá esta
    capability hasta un reinstall — esta aserción local es la que cubre en
    vivo (ver tests/invariants/test_capability_genericity.py)."""

    def test_manifest_has_no_scenario_vocabulary(self) -> None:
        denylist_path = (
            Path(__file__).resolve().parents[3] / "tests" / "invariants" / "scenario_denylist.txt"
        )
        denylist = [
            line.strip().lower()
            for line in denylist_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]

        manifest = TrotterEvolve().manifest
        text = json.dumps(dataclasses.asdict(manifest), default=str).lower()

        violations = [term for term in denylist if term in text]
        assert not violations, f"manifest contiene vocabulario de escenario: {violations}"
