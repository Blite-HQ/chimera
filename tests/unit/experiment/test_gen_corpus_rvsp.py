"""Invariantes del congelador de la curva r-vs-p (`scripts/gen_corpus_rvsp.py`, V3/M20).

`scripts/` no es un paquete instalable — mismo patrón de carga por ruta que
`tests/unit/experiment/test_exp_r_vs_p.py` y `test_import_nexus_runs.py`.

Qué se prueba y qué NO: acá viven las invariantes del RECORD (identidad por
digest, rangos, orden, y que el método quede declarado). Los números de QAOA
NO se aseveran — Qiskit/Aer no es bit-determinista entre versiones (lección
de Task 1), así que un golden sería un test que se rompe solo.

La instancia de trabajo es `cr6-uniforme` (6 qubits, óptimo 5) con p=1 y dos
semillas: el barrido más chico que ejercita el camino completo.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Protocol, cast

import pytest

pytest.importorskip(
    "qiskit", reason="extra opcional: uv sync --all-packages --extra qaoa"
)

_INSTANCIA = "cr6-uniforme"
_SEMILLAS = (1, 2)


class _GenModule(Protocol):
    NEXUS_ANGLES: str
    COBYLA_ANGLES: str

    def record_digest(self, record_without_digest: dict[str, Any]) -> str: ...

    def load_instance(self, name: str) -> tuple[list[list[int]], int]: ...

    def nexus_angles_by_p(
        self, index: dict[str, Any], instance: str
    ) -> dict[int, dict[str, Any]]: ...

    def build_record(
        self,
        *,
        instance: str,
        matrix: list[list[int]],
        optimo: int,
        p_values: tuple[int, ...],
        seeds: tuple[int, ...],
        angle_source: str,
        angles_by_p: dict[int, dict[str, Any]] | None = None,
    ) -> dict[str, Any]: ...


def _find_repo_root() -> Path:
    for base in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        if (base / "scripts" / "gen_corpus_rvsp.py").is_file():
            return base
    msg = "scripts/gen_corpus_rvsp.py no encontrado sobre este archivo"
    raise FileNotFoundError(msg)


def _load_module() -> _GenModule:
    script_path = _find_repo_root() / "scripts" / "gen_corpus_rvsp.py"
    spec = importlib.util.spec_from_file_location("gen_corpus_rvsp", script_path)
    if spec is None or spec.loader is None:
        msg = f"no se pudo construir un spec de import para {script_path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast("_GenModule", module)


gen = _load_module()
_REPO = _find_repo_root()
_NEXUS_INDEX: dict[str, Any] = json.loads(
    (_REPO / "knowledge" / "nexus" / "index.json").read_text(encoding="utf-8")
)


class TestAngulosDeNexus:
    def test_los_angulos_salen_del_indice_con_su_digest(self) -> None:
        """La pieza que V3 hace posible: los ángulos que Quantinuum corrió,
        legibles desde el repo y atados al `circuit_digest` que los cubre."""
        # Act
        por_p = gen.nexus_angles_by_p(_NEXUS_INDEX, "cr8-uniforme")

        # Assert
        assert sorted(por_p) == [1, 2, 3]
        for p, entrada in por_p.items():
            assert len(entrada["betas"]) == p
            assert len(entrada["gammas"]) == p
            assert len(entrada["circuit_digest"]) == 64

    def test_dos_corridas_de_la_misma_capa_tienen_que_coincidir(self) -> None:
        """Dos backends corriendo (instancia, p) SON el mismo circuito lógico.
        Si sus ángulos difirieran, elegir uno en silencio haría que el punto
        de la curva no correspondiera a la mitad de la evidencia."""
        # Arrange
        index = {
            "imports": [
                {
                    "instance": "x",
                    "p": 1,
                    "betas": [0.1],
                    "gammas": [0.2],
                    "circuit_digest": "a" * 64,
                },
                {
                    "instance": "x",
                    "p": 1,
                    "betas": [0.9],
                    "gammas": [0.2],
                    "circuit_digest": "b" * 64,
                },
            ]
        }

        # Act / Assert
        with pytest.raises(ValueError, match="discrepan"):
            gen.nexus_angles_by_p(index, "x")

    def test_una_instancia_sin_corridas_no_inventa_angulos(self) -> None:
        # Act
        por_p = gen.nexus_angles_by_p(_NEXUS_INDEX, "ieee30-flujo")

        # Assert — vacío honesto; quien lo consuma decide, nunca este módulo
        assert por_p == {}


class TestRecordCongelado:
    @staticmethod
    def _record(**extra: Any) -> dict[str, Any]:
        matrix, optimo = gen.load_instance(_INSTANCIA)
        angles = gen.nexus_angles_by_p(_NEXUS_INDEX, _INSTANCIA)
        return gen.build_record(
            instance=_INSTANCIA,
            matrix=matrix,
            optimo=optimo,
            p_values=(1,),
            seeds=_SEMILLAS,
            angle_source=gen.NEXUS_ANGLES,
            angles_by_p={1: angles[1]},
            **extra,
        )

    def test_el_digest_cierra_sobre_su_propio_contenido(self) -> None:
        """Misma regla de identidad que el resto del corpus (§15.3): el
        record es lo que su digest dice, o no se carga."""
        # Act
        record = self._record()

        # Assert
        sin_digest = {k: v for k, v in record.items() if k != "digest"}
        assert record["digest"] == gen.record_digest(sin_digest)

    def test_toda_razon_vive_entre_cero_y_uno(self) -> None:
        """El contrato del wire lo exige (`rvspSchema` rechaza r fuera de
        [0,1]); si la ciencia produjera un r>1 hay que mirarla, no recortarla."""
        # Act
        record = self._record()

        # Assert
        for punto in record["points"]:
            for campo in (
                "r_esperado_mean",
                "r_muestral_mean",
                "r_muestral_min",
                "r_muestral_max",
                "success_rate",
            ):
                assert 0.0 <= punto[campo] <= 1.0, (campo, punto[campo])
            assert punto["r_muestral_std"] >= 0.0
        for baseline in record["baselines"].values():
            assert 0.0 <= baseline["r"] <= 1.0

    def test_el_metodo_declara_de_donde_salieron_los_angulos(self) -> None:
        """La ETIQUETA de la curva: sin ella, un punto medido en ángulos de
        hardware y uno medido en ángulos que optimizamos nosotros se ven
        idénticos, y son afirmaciones distintas."""
        # Act
        record = self._record()

        # Assert
        metodo = record["metodo"]
        assert metodo["angle_source"] == gen.NEXUS_ANGLES
        assert metodo["backend"] == "aer_simulator"
        assert metodo["seeds"] == list(_SEMILLAS)
        assert metodo["angle_digests"] == {
            "1": gen.nexus_angles_by_p(_NEXUS_INDEX, _INSTANCIA)[1]["circuit_digest"]
        }

    def test_las_tres_baselines_del_contrato_estan_completas(self) -> None:
        """`baselines` está CERRADO a 3 claves por contrato (C-15): se
        extiende coordinado, jamás con un catchall."""
        # Act
        record = self._record()

        # Assert
        assert set(record["baselines"]) == {"cpsat", "greedy", "gw"}
        assert record["baselines"]["cpsat"]["r"] == 1.0

    def test_una_instancia_sin_optimo_no_produce_curva(self) -> None:
        """`ice-*` tiene `optimo: null` — sin denominador no hay r, y una
        curva fabricada está prohibida (letra C-9/freeze §15.3 C-10)."""
        with pytest.raises(ValueError, match="optimo"):
            gen.load_instance("ice-uniforme")
