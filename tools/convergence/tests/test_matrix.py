"""Las reglas que impiden un veredicto no ganado.

Cada test de acá corresponde a un modo de falla observado en la única corrida
real del protocolo: tres ejes que estaban en A y no debían estarlo. El sesgo
tiene dirección —quien arma la matriz quiere que converja— y estas reglas son
esa dirección, cerrada.
"""

from __future__ import annotations

import pytest

from chimera_convergence.matrix import (
    Attestation,
    Axis,
    MatrixError,
    Quadrant,
    Severity,
    tally,
    verdict,
)

INTACTAS = Attestation(holds=True, evidence="grep sobre invariants.md: cero tocadas")
SOBREVIVIO = Attestation(holds=True, evidence="stress independiente sobre HEAD: GO")


def _eje(
    axis_id: str = "E-1",
    quadrant: Quadrant = Quadrant.CONVERGENCE,
    **kwargs: object,
) -> Axis:
    base: dict[str, object] = {
        "id": axis_id,
        "what": "un defecto",
        "artifact": "modulo.py",
        "quadrant": quadrant,
        "source_a_evidence": "acta §4",
        "source_b_evidence": "corrida propia",
    }
    base.update(kwargs)
    return Axis(**base)  # type: ignore[arg-type]


class TestElCuadranteA:
    """Donde duele: A es lo que sostiene el veredicto."""

    def test_sin_evidencia_de_las_dos_fuentes_no_es_convergencia(self) -> None:
        """El modo de falla es la ósmosis: el auditor ya sabía qué buscar.

        Sin evidencia primaria propia de cada lado, «coincidimos» no distingue
        una convergencia real de un auditor recordando la otra fuente.
        """
        with pytest.raises(MatrixError, match="evidencia primaria de AMBAS"):
            tally([_eje(source_b_evidence="")])

    def test_una_convergencia_parcial_sin_el_test_del_paraguas_se_rechaza(
        self,
    ) -> None:
        with pytest.raises(MatrixError, match="paraguas"):
            tally([_eje(variant="parcial")])

    def test_una_parcial_que_falla_el_paraguas_tampoco_pasa(self) -> None:
        """Registrar el juicio no basta: tiene que haberlo pasado."""
        with pytest.raises(MatrixError, match="paraguas"):
            tally([_eje(variant="parcial", umbrella=False)])

    def test_una_parcial_que_lo_pasa_cuenta(self) -> None:
        counts = tally([_eje(variant="parcial", umbrella=True)])
        assert counts.by_quadrant["A"] == 1


class TestLosDemasCuadrantes:
    def test_una_ganancia_exige_que_la_otra_fuente_callara(self) -> None:
        with pytest.raises(MatrixError, match="ninguna de A"):
            tally([_eje(quadrant=Quadrant.GAIN)])

    def test_un_silencio_exige_que_la_fuente_b_callara(self) -> None:
        with pytest.raises(MatrixError, match="ninguna de B"):
            tally([_eje(quadrant=Quadrant.SILENCE, variant="verificable")])

    def test_un_silencio_debe_decir_si_es_verificable_o_de_dueño(self) -> None:
        """La distinción decide qué se hace: aplicar por piso, o escalar.

        Sin ella, el silencio de un dueño se aplicaría solo, que es justo lo
        que el cuadrante C existe para impedir.
        """
        with pytest.raises(MatrixError, match="variante"):
            tally([_eje(quadrant=Quadrant.SILENCE, source_b_evidence="")])

    def test_un_conflicto_exige_las_dos_versiones(self) -> None:
        with pytest.raises(MatrixError, match="se contradicen"):
            tally([_eje(quadrant=Quadrant.CONFLICT, source_a_evidence="")])

    def test_un_eje_duplicado_se_rechaza(self) -> None:
        """Contar dos veces el mismo defecto infla cualquier cifra."""
        with pytest.raises(MatrixError, match="duplicado"):
            tally([_eje("E-1"), _eje("E-1")])


class TestCuantificacion:
    def test_la_tasa_se_mide_sobre_lo_que_la_fuente_b_afirmo(self) -> None:
        """Medirla sobre el total premiaría a una fuente A que dispara mucho.

        Cada silencio suyo bajaría el denominador y subiría la tasa sin que
        nadie haya coincidido en nada.
        """
        axes = [
            _eje("A-1"),
            _eje("A-2"),
            _eje("B-1", Quadrant.GAIN, source_a_evidence=""),
            _eje("C-1", Quadrant.SILENCE, variant="verificable", source_b_evidence=""),
            _eje("C-2", Quadrant.SILENCE, variant="dueño", source_b_evidence=""),
        ]
        counts = tally(axes)
        assert counts.total == 5
        assert counts.asserted_by_b == 3  # A+A+B, los C no cuentan
        assert counts.convergence_rate == pytest.approx(2 / 3)

    def test_reporta_los_puntos_ciegos_y_los_silencios_por_separado(self) -> None:
        """Son preguntas distintas: para qué sirve la otra fuente, y cuánto se
        aplica por piso."""
        counts = tally(
            [
                _eje("B-1", Quadrant.GAIN, source_a_evidence=""),
                _eje("C-1", Quadrant.SILENCE, variant="dueño", source_b_evidence=""),
            ]
        )
        assert counts.blind_spots_of_a == 1
        assert counts.silences_of_b == 1

    def test_una_matriz_vacia_no_divide_por_cero(self) -> None:
        assert tally([]).convergence_rate == 0.0


class TestVeredicto:
    def test_converge_con_los_cuatro_criterios(self) -> None:
        resultado = verdict(
            [_eje()],
            frozen_decisions_intact=INTACTAS,
            substance_survived=SOBREVIVIO,
        )
        assert resultado.converge
        assert resultado.reasons == ()

    def test_un_conflicto_sin_resolver_lo_bloquea(self) -> None:
        resultado = verdict(
            [_eje("D-1", Quadrant.CONFLICT)],
            frozen_decisions_intact=INTACTAS,
            substance_survived=SOBREVIVIO,
        )
        assert not resultado.converge
        assert any("sin resolver" in reason for reason in resultado.reasons)

    def test_un_conflicto_resuelto_no_lo_bloquea(self) -> None:
        """Decisión de dueño acatada y supersesión aplicada: se documenta, no
        detiene."""
        resultado = verdict(
            [_eje("D-1", Quadrant.CONFLICT, variant="resuelto")],
            frozen_decisions_intact=INTACTAS,
            substance_survived=SOBREVIVIO,
        )
        assert resultado.converge

    def test_un_p0_sin_fix_lo_bloquea_y_lo_nombra(self) -> None:
        resultado = verdict(
            [_eje("E-9", severity=Severity.P0)],
            frozen_decisions_intact=INTACTAS,
            substance_survived=SOBREVIVIO,
        )
        assert not resultado.converge
        assert any("E-9" in reason for reason in resultado.reasons)

    def test_sin_declarar_los_criterios_no_computables_no_hay_veredicto(self) -> None:
        """El corazón del fail-closed.

        «Ninguna decisión congelada invalidada» no se deduce de la matriz. Un
        veredicto que se emite igual es un veredicto que nadie comprobó.
        """
        resultado = verdict([_eje()])
        assert not resultado.converge
        assert len(resultado.reasons) == 2

    def test_un_criterio_declarado_sin_evidencia_no_cuenta(self) -> None:
        """Marcar `holds = true` y dejar la evidencia vacía es afirmar sin
        mostrar: nadie más puede comprobarlo."""
        resultado = verdict(
            [_eje()],
            frozen_decisions_intact=Attestation(holds=True, evidence="   "),
            substance_survived=SOBREVIVIO,
        )
        assert not resultado.converge
        assert any("sin evidencia" in reason for reason in resultado.reasons)

    def test_un_criterio_que_no_se_sostiene_lo_bloquea_con_su_motivo(self) -> None:
        resultado = verdict(
            [_eje()],
            frozen_decisions_intact=Attestation(
                holds=False, evidence="INV-2 quedó invalidada por el cambio X"
            ),
            substance_survived=SOBREVIVIO,
        )
        assert not resultado.converge
        assert any("INV-2" in reason for reason in resultado.reasons)
