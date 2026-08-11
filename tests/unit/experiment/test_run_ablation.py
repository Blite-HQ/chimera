"""Invariantes del productor de ablación (`scripts/run_ablation.py`, V2/M19).

Carga por ruta (mismo patrón que `test_exp_r_vs_p.py`). Lo que se prueba son
las reglas de HONESTIDAD del reporte, que es donde este script puede mentir:
qué número reporta cada brazo, cuándo NO reporta ninguno, y qué brazos
declara.

Correr los tres brazos de verdad cuesta ~30 s de Aer y ya está cubierto por
los tests de cada capability — acá se ejercitan los extractores puros.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Protocol, cast

import pytest


class _AblationModule(Protocol):
    def build_arms(
        self, matrix: list[list[int]], *, layers: int, seed: int
    ) -> list[Any]: ...

    def load_matrix(self, name: str) -> tuple[list[list[int]], int | None]: ...

    def expected_energy_of(self, salida: dict[str, Any]) -> float | None: ...
    def exact_energy_of(self, salida: dict[str, Any]) -> float | None: ...
    def mitigated_energy_of(self, salida: dict[str, Any]) -> float | None: ...


def _find_repo_root() -> Path:
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        if (base / "scripts" / "run_ablation.py").is_file():
            return base
    msg = "scripts/run_ablation.py no encontrado sobre este archivo"
    raise FileNotFoundError(msg)


def _load_module() -> _AblationModule:
    script_path = _find_repo_root() / "scripts" / "run_ablation.py"
    spec = importlib.util.spec_from_file_location("run_ablation", script_path)
    if spec is None or spec.loader is None:
        msg = f"no se pudo construir un spec de import para {script_path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast("_AblationModule", module)


prod = _load_module()


class TestQueNumeroReportaCadaBrazo:
    """Las barras del panel tienen que ser la MISMA clase de número. Mezclar
    un best-of-samples con un valor esperado haría ver a la mitigación peor
    por una razón que no tiene nada que ver con mitigar."""

    def test_el_brazo_cuantico_reporta_el_valor_esperado_no_el_mejor_shot(
        self,
    ) -> None:
        # Arrange — `energy` (best-of-2048) alcanza el óptimo casi siempre en
        # instancias chicas; es un artefacto de muestreo (fix 4b)
        salida = {"energy": 7.0, "expected_energy": 6.35}

        # Act / Assert
        assert prod.expected_energy_of(salida) == 6.35

    def test_el_brazo_exacto_reporta_su_optimo(self) -> None:
        assert prod.exact_energy_of({"energy": 7.0}) == 7.0

    def test_un_brazo_sin_el_campo_no_inventa_un_cero(self) -> None:
        assert prod.expected_energy_of({}) is None
        assert prod.exact_energy_of({}) is None


class TestLaReglaDePublicacionDelBrazoMitigado:
    def test_reporta_el_valor_mitigado_cuando_sobrevivio_al_control(self) -> None:
        # Arrange
        salida = {"mitigated_energy": 5.94, "improvement_survives_control": True}

        # Act / Assert
        assert prod.mitigated_energy_of(salida) == 5.94

    def test_no_reporta_nada_cuando_el_control_lo_desautoriza(self) -> None:
        """arXiv:2607.09360: una mejora que el control negativo iguala o supera
        es artefacto de la extrapolación. Publicar ese número en el panel sería
        exactamente el error que el control existe para evitar."""
        # Arrange
        salida = {"mitigated_energy": 5.94, "improvement_survives_control": False}

        # Act / Assert
        assert prod.mitigated_energy_of(salida) is None

    def test_sin_veredicto_del_control_tampoco_publica(self) -> None:
        """Fail-closed: una salida sin el campo viene de una versión que no
        corrió el control, y «no sé si es artefacto» no es «no lo es»."""
        assert prod.mitigated_energy_of({"mitigated_energy": 5.94}) is None


class TestExtraccionSinDrift:
    """Ceremonia #177: `build_arms`/los tres lectores de energía se movieron
    a `blite.runtime.ablation` para que `chimera_api.runs` los consuma sin
    importar este script (no instalable). El script queda como CLIENTE
    delgado — esto comprueba que lo es de VERDAD: mismo objeto función, no
    una reimplementación paralela que podría driftear."""

    def test_el_script_reexporta_los_mismos_objetos_que_el_motor(self) -> None:
        from blite.runtime import ablation as motor

        assert prod.build_arms is motor.build_arms
        assert prod.expected_energy_of is motor.expected_energy_of
        assert prod.exact_energy_of is motor.exact_energy_of
        assert prod.mitigated_energy_of is motor.mitigated_energy_of


class TestBrazosDeclarados:
    def test_declara_los_tres_que_tienen_productor_real(self) -> None:
        # Act
        brazos = prod.build_arms([[1, -1], [-1, 1]], layers=1, seed=1)

        # Assert
        assert [b.variant for b in brazos] == ["quantum", "classical", "zne"]

    def test_no_declara_mitigated_porque_su_productor_es_v9(self) -> None:
        """Un brazo declarado sin productor sería una barra vacía CON nombre —
        peor que una barra ausente, porque anuncia una comparación que no
        ocurrió."""
        # Act
        brazos = prod.build_arms([[1, -1], [-1, 1]], layers=1, seed=1)

        # Assert
        assert "mitigated" not in {b.variant for b in brazos}

    def test_ningun_brazo_declara_su_costo_por_adelantado(self) -> None:
        """El costo de corte ES lo que el brazo computa: declararlo antes
        obligaría a correr la capability dos veces y el `wall_ms` registrado
        mediría la segunda."""
        # Act
        brazos = prod.build_arms([[1, -1], [-1, 1]], layers=1, seed=1)

        # Assert
        for brazo in brazos:
            assert brazo.cut_cost is None
            assert brazo.cut_cost_from is not None


class TestCorpus:
    def test_una_instancia_sin_optimo_se_reporta_como_tal(self) -> None:
        """`ice-*` no tiene óptimo congelado: la ablación SÍ corre (los costos
        son comparables entre sí), pero `r` no existe y no se fabrica."""
        # Act
        _matrix, optimo = prod.load_matrix("ice-uniforme")

        # Assert
        assert optimo is None

    def test_el_transform_a_qubo_es_el_canonico(self) -> None:
        # Act — cr6-uniforme: 6 nodos, 6 aristas de peso 1, óptimo 5
        matrix, optimo = prod.load_matrix("cr6-uniforme")

        # Assert — la diagonal es el grado ponderado; fuera, −peso
        assert optimo == 5
        assert len(matrix) == 6
        assert matrix[0][1] == -1
        assert matrix[0][0] == pytest.approx(4)  # nodo 0 toca 4 aristas
