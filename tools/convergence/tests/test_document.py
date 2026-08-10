"""La matriz en TOML: cargarla, evaluarla y correrla desde la línea de comandos."""

from __future__ import annotations

from pathlib import Path

import pytest

from chimera_convergence.__main__ import main
from chimera_convergence.document import evaluate, load, render
from chimera_convergence.matrix import MatrixError, Quadrant

COMPLETA = """
[tracks]
a = "la simulación"
b = "la ratificación real"

[attestations.frozen_decisions_intact]
holds = true
evidence = "grep sobre invariants.md — cero decisiones tocadas"

[attestations.substance_survived]
holds = true
evidence = "stress independiente sobre HEAD final: GO"

[[axis]]
id = "E-1"
what = "las semillas no llegan a la máquina de estados"
artifact = "run_loop.py"
quadrant = "A"
source_a_evidence = "acta sim §4.2"
source_b_evidence = "corrida propia, run_loop.py:210"
severity = "P0"
fix_available = true
disposition = "portar el fix"

[[axis]]
id = "E-2"
what = "el Studio no tiene revisor"
artifact = "apps/studio"
quadrant = "C"
variant = "dueño"
source_a_evidence = "acta sim §6"
"""


def _escribir(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "matriz.toml"
    path.write_text(body, encoding="utf-8")
    return path


class TestCarga:
    def test_lee_los_ejes_y_las_declaraciones(self, tmp_path: Path) -> None:
        axes, attestations = load(_escribir(tmp_path, COMPLETA))
        assert [axis.id for axis in axes] == ["E-1", "E-2"]
        assert axes[0].quadrant is Quadrant.CONVERGENCE
        assert attestations["frozen_decisions_intact"] is not None

    def test_una_declaracion_ausente_queda_en_none_no_en_un_default_optimista(
        self, tmp_path: Path
    ) -> None:
        """Un criterio que nadie escribió es un criterio que nadie comprobó."""
        _, attestations = load(
            _escribir(
                tmp_path, "[[axis]]\nid = 'x'\nquadrant='B'\nsource_b_evidence='y'\n"
            )
        )
        assert attestations["frozen_decisions_intact"] is None
        assert attestations["substance_survived"] is None

    def test_un_eje_sin_id_explota(self, tmp_path: Path) -> None:
        with pytest.raises(MatrixError, match="sin `id`"):
            load(_escribir(tmp_path, "[[axis]]\nquadrant = 'A'\n"))

    def test_un_cuadrante_inventado_explota_nombrando_los_validos(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(MatrixError, match="no es válido"):
            load(_escribir(tmp_path, "[[axis]]\nid = 'x'\nquadrant = 'Z'\n"))

    def test_toml_roto_explota(self, tmp_path: Path) -> None:
        with pytest.raises(MatrixError, match="TOML inválido"):
            load(_escribir(tmp_path, "esto no [ es toml"))

    def test_el_paraguas_es_un_juicio_no_un_texto(self, tmp_path: Path) -> None:
        with pytest.raises(MatrixError, match="juicio"):
            load(
                _escribir(
                    tmp_path, "[[axis]]\nid = 'x'\nquadrant = 'A'\numbrella = 'sí'\n"
                )
            )


class TestEvaluacion:
    def test_una_matriz_completa_converge(self, tmp_path: Path) -> None:
        assert evaluate(_escribir(tmp_path, COMPLETA)).converge

    def test_el_reporte_nombra_el_veredicto_y_las_cifras(self, tmp_path: Path) -> None:
        salida = render(evaluate(_escribir(tmp_path, COMPLETA)))
        assert "CONVERGEN" in salida
        assert "puntos ciegos" in salida


class TestLineaDeComandos:
    def test_converger_sale_cero(self, tmp_path: Path) -> None:
        assert main([str(_escribir(tmp_path, COMPLETA))]) == 0

    def test_divergir_sale_uno(self, tmp_path: Path) -> None:
        """Misma matriz, sin las declaraciones: no hay veredicto que emitir."""
        sin_declaraciones = "\n".join(
            linea
            for bloque in COMPLETA.split("\n\n")
            if not bloque.lstrip().startswith("[attestations")
            for linea in (bloque,)
        )
        assert "[attestations" not in sin_declaraciones
        assert main([str(_escribir(tmp_path, sin_declaraciones))]) == 1

    def test_una_matriz_rota_sale_dos_y_no_uno(self, tmp_path: Path) -> None:
        """«No se pudo leer» NO es «divergen».

        Confundirlas dejaría pasar un archivo roto como si fuera un hallazgo, y
        un gate encadenado a esto trataría un error de sintaxis como una
        conclusión sobre el trabajo.
        """
        assert main([str(_escribir(tmp_path, "esto no [ es toml"))]) == 2

    def test_un_archivo_que_no_existe_tambien_sale_dos(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / "fantasma.toml")]) == 2
