"""`blite.runtime.ablation.build_arms` — V9 le da productor a `mitigated`.

`build_arms` en sí (a diferencia de `run_ablation_arms`, cubierto en
`test_ablation.py`) no tenía test propio: los tres brazos con productor real
se cubrían indirectamente vía `tests/unit/experiment/test_run_ablation.py`
(que carga `scripts/run_ablation.py` por ruta). Este archivo prueba la regla
de declaración en sí, incluida la guarda de no-regresión que la tarea exige:
los otros tres brazos quedan IDÉNTICOS se declare o no `mitigated`.
"""

from __future__ import annotations

import pytest

from blite.runtime import ablation

_MATRIX = [[1, -1], [-1, 1]]


class TestGuardaDeNoRegresion:
    """Los brazos `quantum`/`classical`/`zne` no pueden cambiar por la
    presencia o ausencia del productor de `mitigated` — son independientes
    por construcción (se agregan/no se agregan, nunca se modifican)."""

    def test_los_tres_brazos_existentes_son_identicos_con_o_sin_productor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        con_productor = ablation.build_arms(_MATRIX, layers=1, seed=1)

        monkeypatch.setattr(ablation, "_mitigated_producer_available", lambda: False)
        sin_productor = ablation.build_arms(_MATRIX, layers=1, seed=1)

        primeros_tres_con = [b for b in con_productor if b.variant != "mitigated"]
        assert primeros_tres_con == sin_productor


class TestDeclaracionDeMitigated:
    def test_se_declara_cuando_el_productor_esta_disponible(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ablation, "_mitigated_producer_available", lambda: True)

        brazos = ablation.build_arms(_MATRIX, layers=2, seed=7)

        mitigado = next(b for b in brazos if b.variant == "mitigated")
        assert mitigado.capability_id == "blite.quantum.zne"
        assert mitigado.inputs == {
            "matrix": _MATRIX,
            "layers": 2,
            "seed": 7,
            "method": ablation._MITIGATED_METHOD,  # pyright: ignore[reportPrivateUsage] — comprobando la réplica que ADR-008 obliga
        }
        assert mitigado.cut_cost_from is ablation.mitigated_energy_of

    def test_no_se_declara_cuando_el_productor_no_esta_disponible(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ablation, "_mitigated_producer_available", lambda: False)

        brazos = ablation.build_arms(_MATRIX, layers=1, seed=1)

        assert "mitigated" not in {b.variant for b in brazos}
        assert len(brazos) == 3

    def test_fail_loud_dentro_del_stream_nunca_un_500(self) -> None:
        """La sonda de disponibilidad (`find_spec`) no puede lanzar — un
        módulo ausente es `None`, jamás una excepción que tumbe el arranque
        HTTP del modo ablación."""
        assert ablation._mitigated_producer_available() in (  # pyright: ignore[reportPrivateUsage] — la sonda ES lo que este test ejercita
            True,
            False,
        )


class TestSincroniaConElCorrector:
    """`build_arms` no puede importar `blite_cap_quantum` (ADR-008: el
    engine no importa paquetes de capability) y por eso replica el nombre
    del método a mano (`_MITIGATED_METHOD`) — este test SÍ puede importar
    ambos lados y comprueba que no driftearon en silencio."""

    def test_el_metodo_declarado_coincide_con_el_primario_del_corrector(self) -> None:
        pytest.importorskip("sklearn")
        from blite_cap_quantum.corrector import PRIMARY_METHOD

        assert (
            ablation._MITIGATED_METHOD  # pyright: ignore[reportPrivateUsage] — la réplica ES lo que este test comprueba
            == PRIMARY_METHOD
        )
