"""Warm start e inicialización explícita de ángulos en `solve_qaoa` (V5).

Dos capacidades nuevas, ambas ADITIVAS (sin argumentos, `solve_qaoa` se
comporta exactamente igual que antes):

1. **Ángulos dados** (`initial_angles` + `optimize=False`) — evaluar QAOA en
   un calendario que vino de AFUERA. Es lo que permite reportar ⟨C⟩ en los
   ángulos de una corrida ajena sin re-optimizar (y por tanto sin cambiar los
   ángulos que esa corrida usó, que es justo lo que la haría incomparable).
2. **INTERP** (`init_strategy="interp"`) — subir la escalera p=1…layers
   arrancando cada nivel del óptimo interpolado del anterior.

Invariantes, no goldens: Qiskit/Aer no es bit-determinista entre versiones
(misma lección que Task 1). Lo que sí es exacto y se asevera acá es el
ROUND-TRIP — optimizar, devolver los ángulos, re-evaluar en ellos y obtener
el mismo ⟨C⟩ — porque ambos lados calculan la misma expectativa sobre el
mismo statevector dentro de la misma corrida.
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip(
    "qiskit", reason="extra opcional: uv sync --all-packages --extra qaoa"
)

from blite_cap_quantum import QaoaSolver  # noqa: E402
from blite_cap_quantum.qaoa import solve_qaoa  # noqa: E402

# G6 de knowledge/quantum/02 §1.2 — óptimo 5 en [0,0,1] (o su complemento)
_G6 = [[4, -1, -3], [-1, 3, -2], [-3, -2, 5]]


def _angulos(resultado: dict[str, Any]) -> dict[str, list[float]]:
    return {
        "betas": resultado["angles"]["betas"],
        "gammas": resultado["angles"]["gammas"],
    }


class TestAngulosReportados:
    def test_los_angulos_usados_siempre_se_reportan(self) -> None:
        """Sin los ángulos, `expected_energy` es un número que nadie puede
        recomputar: el circuito que lo produjo quedaría sin identificar."""
        # Act
        resultado = solve_qaoa(_G6, layers=2, seed=1)

        # Assert
        assert len(resultado["angles"]["betas"]) == 2
        assert len(resultado["angles"]["gammas"]) == 2
        assert resultado["init_strategy"] == "constant"
        assert resultado["optimized"] is True


class TestAngulosDados:
    def test_evaluar_en_angulos_dados_reproduce_la_energia_esperada(self) -> None:
        """El round-trip que hace comparables dos corridas: optimizar, tomar
        los ángulos que salieron y re-evaluar en ellos da EXACTAMENTE el mismo
        ⟨C⟩. Si no cerrara, los ángulos reportados no serían los usados."""
        # Arrange
        optimizado = solve_qaoa(_G6, layers=2, seed=1)

        # Act
        reevaluado = solve_qaoa(
            _G6, layers=2, seed=1, initial_angles=_angulos(optimizado), optimize=False
        )

        # Assert
        assert reevaluado["expected_energy"] == pytest.approx(
            optimizado["expected_energy"], rel=1e-12
        )
        assert reevaluado["angles"] == optimizado["angles"]
        assert reevaluado["optimized"] is False
        assert reevaluado["init_strategy"] == "given"

    def test_angulos_distintos_dan_energias_distintas(self) -> None:
        """Control de que `optimize=False` NO está optimizando a escondidas:
        si lo hiciera, dos puntos de arranque distintos convergerían al mismo
        ⟨C⟩ y el número dejaría de ser el de los ángulos pedidos."""
        # Arrange
        uno = solve_qaoa(
            _G6,
            layers=1,
            seed=1,
            initial_angles={"betas": [0.1], "gammas": [0.1]},
            optimize=False,
        )
        otro = solve_qaoa(
            _G6,
            layers=1,
            seed=1,
            initial_angles={"betas": [0.9], "gammas": [1.3]},
            optimize=False,
        )

        # Assert
        assert uno["expected_energy"] != otro["expected_energy"]

    def test_los_angulos_dados_se_usan_como_arranque_al_optimizar(self) -> None:
        """`initial_angles` con `optimize=True` es un warm start: mueve el
        punto de partida de COBYLA, así que el óptimo local alcanzado puede
        diferir del que se alcanza desde el arranque constante."""
        # Act
        tibio = solve_qaoa(
            _G6,
            layers=2,
            seed=1,
            initial_angles={"betas": [0.9, 0.4], "gammas": [1.1, 0.6]},
        )

        # Assert
        assert tibio["optimized"] is True
        assert tibio["init_strategy"] == "given"

    def test_no_optimizar_sin_angulos_explota(self) -> None:
        """Sin ángulos, `optimize=False` evaluaría en el arranque constante
        arbitrario y lo reportaría como si fuera un resultado."""
        with pytest.raises(ValueError, match="initial_angles"):
            solve_qaoa(_G6, layers=2, optimize=False)

    def test_angulos_de_otro_largo_explotan(self) -> None:
        with pytest.raises(ValueError, match="2 capas"):
            solve_qaoa(_G6, layers=2, initial_angles={"betas": [0.1], "gammas": [0.2]})

    def test_faltar_una_familia_de_angulos_explota(self) -> None:
        with pytest.raises(ValueError, match="gammas"):
            solve_qaoa(_G6, layers=1, initial_angles={"betas": [0.1]})

    def test_angulos_dados_e_interp_son_excluyentes(self) -> None:
        """Dos respuestas distintas a «de dónde arranca el optimizador»; la
        silenciosa sería que una gane y el reporte diga la otra."""
        with pytest.raises(ValueError, match="excluyentes"):
            solve_qaoa(
                _G6,
                layers=1,
                initial_angles={"betas": [0.1], "gammas": [0.2]},
                init_strategy="interp",
            )

    def test_una_estrategia_desconocida_explota(self) -> None:
        with pytest.raises(ValueError, match="init_strategy"):
            solve_qaoa(_G6, layers=1, init_strategy="recocido")


class TestInterp:
    def test_la_escalera_recorre_todos_los_niveles(self) -> None:
        """INTERP no es un arranque: es una escalera. Cada peldaño queda
        registrado con su ⟨C⟩, así que la curva r vs p de una corrida INTERP
        se lee del propio resultado en vez de re-correr el barrido."""
        # Act
        resultado = solve_qaoa(_G6, layers=3, seed=1, init_strategy="interp")

        # Assert
        escalera = resultado["warm_start_levels"]
        assert [nivel["p"] for nivel in escalera] == [1, 2, 3]
        assert escalera[-1]["expected_energy"] == pytest.approx(
            resultado["expected_energy"], rel=1e-12
        )
        assert resultado["init_strategy"] == "interp"

    def test_cada_peldano_reporta_los_angulos_de_su_nivel(self) -> None:
        # Act
        resultado = solve_qaoa(_G6, layers=3, seed=1, init_strategy="interp")

        # Assert
        for nivel in resultado["warm_start_levels"]:
            assert len(nivel["betas"]) == nivel["p"]
            assert len(nivel["gammas"]) == nivel["p"]

    def test_con_una_capa_coincide_con_el_arranque_constante(self) -> None:
        """En p=1 no hay nivel anterior del cual interpolar, así que INTERP
        degenera al arranque constante — y lo hace exactamente, no «parecido»."""
        # Arrange
        constante = solve_qaoa(_G6, layers=1, seed=1)

        # Act
        interpolado = solve_qaoa(_G6, layers=1, seed=1, init_strategy="interp")

        # Assert
        assert interpolado["expected_energy"] == pytest.approx(
            constante["expected_energy"], rel=1e-12
        )
        assert interpolado["angles"] == constante["angles"]

    def test_sin_interp_no_hay_escalera(self) -> None:
        """Honest-empty: una corrida que no subió la escalera no publica una
        escalera de un peldaño con cara de barrido."""
        # Act
        resultado = solve_qaoa(_G6, layers=2, seed=1)

        # Assert
        assert "warm_start_levels" not in resultado


class TestSuperficieDeLaCapability:
    """Lo que el manifest declara ES el contrato: un input que la
    implementación acepta pero el manifest calla es una capacidad que ningún
    orquestador puede pedir sin leer el código."""

    def test_el_manifest_declara_los_ingresos_nuevos(self) -> None:
        # Act
        propiedades = QaoaSolver().manifest.input_schema["properties"]

        # Assert
        assert set(propiedades) >= {"initial_angles", "optimize", "init_strategy"}
        assert propiedades["init_strategy"]["enum"] == ["constant", "interp"]

    def test_el_manifest_declara_los_egresos_nuevos(self) -> None:
        # Act
        propiedades = QaoaSolver().manifest.output_schema["properties"]

        # Assert
        assert set(propiedades) >= {
            "angles",
            "init_strategy",
            "optimized",
            "warm_start_levels",
        }

    def test_la_capability_evalua_en_los_angulos_dados(self) -> None:
        """La ruta completa por `invoke`: lo que llega por el manifest es lo
        que `solve_qaoa` usa, sin traducción de por medio."""
        # Arrange
        optimizado = QaoaSolver().invoke({"matrix": _G6, "layers": 1, "seed": 1})

        # Act
        reevaluado = QaoaSolver().invoke(
            {
                "matrix": _G6,
                "layers": 1,
                "seed": 1,
                "initial_angles": _angulos(optimizado),
                "optimize": False,
            }
        )

        # Assert — `optimized` es lo que distingue el round-trip real de dos
        # corridas idénticas que coinciden por casualidad de configuración
        assert reevaluado["optimized"] is False
        assert reevaluado["init_strategy"] == "given"
        assert reevaluado["angles"] == optimizado["angles"]
        assert reevaluado["expected_energy"] == pytest.approx(
            optimizado["expected_energy"], rel=1e-12
        )

    def test_optimize_no_booleano_explota(self) -> None:
        """`optimize: "false"` es verdadero en Python — un string colado acá
        re-optimizaría en silencio los ángulos que se pidió NO tocar."""
        with pytest.raises(ValueError, match="optimize"):
            QaoaSolver().invoke({"matrix": _G6, "optimize": "false"})

    def test_init_strategy_no_textual_explota(self) -> None:
        with pytest.raises(ValueError, match="init_strategy"):
            QaoaSolver().invoke({"matrix": _G6, "init_strategy": 2})
