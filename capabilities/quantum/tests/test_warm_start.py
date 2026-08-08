"""INTERP — la interpolación de ángulos de nivel p a nivel p+1 (V5).

Por qué esta pieza vive sola y sin qiskit: es aritmética pura y por tanto
verificable EXACTAMENTE. Enterrada dentro de `solve_qaoa` solo se podría
comprobar de refilón ("la energía mejoró"), que es justo el tipo de aserción
que pasa aunque la fórmula esté mal.

La fórmula es la de Zhou et al. (2020), §IV — con γ₀ ≡ γ_{p+1} ≡ 0:

    γᵢ^(p+1) = ((i−1)/p)·γ_{i−1}^(p) + ((p−i+1)/p)·γᵢ^(p),   i = 1…p+1
"""

from __future__ import annotations

import pytest

from blite_cap_quantum.warm_start import interp_angles


class TestInterp:
    def test_un_solo_nivel_se_duplica(self) -> None:
        """p=1 → p=2 no tiene nada que interpolar: los dos ángulos nuevos son
        el viejo. Es el caso base de la recursión y el que fija el signo de
        los coeficientes — si estuvieran cruzados, acá saldría un cero."""
        # Arrange / Act
        siguiente = interp_angles([0.7])

        # Assert
        assert siguiente == (0.7, 0.7)

    def test_el_punto_intermedio_es_el_promedio(self) -> None:
        """p=2 → p=3: los extremos se conservan y el del medio es la media —
        el caso más chico donde la interpolación hace trabajo real."""
        # Arrange / Act
        siguiente = interp_angles([0.2, 0.8])

        # Assert
        assert siguiente == pytest.approx((0.2, 0.5, 0.8))

    def test_cada_paso_agrega_exactamente_una_capa(self) -> None:
        # Arrange
        angulos: tuple[float, ...] = (0.1,)

        # Act / Assert — la escalera p=1…6 sube de a una, nunca de a dos
        for esperado in range(2, 7):
            angulos = interp_angles(angulos)
            assert len(angulos) == esperado

    def test_los_extremos_del_calendario_se_conservan(self) -> None:
        """Consecuencia directa de γ₀ = γ_{p+1} = 0: el primer y el último
        ángulo pasan intactos. Es lo que hace que INTERP EXTIENDA un
        calendario en vez de reemplazarlo."""
        # Arrange
        original = [0.3, -0.9, 1.4, 0.05]

        # Act
        siguiente = interp_angles(original)

        # Assert
        assert siguiente[0] == pytest.approx(original[0])
        assert siguiente[-1] == pytest.approx(original[-1])

    def test_un_calendario_constante_sigue_constante(self) -> None:
        """Los coeficientes suman 1 en cada i (son una combinación convexa):
        si todos los ángulos son iguales, interpolar no puede moverlos. Un
        error de normalización rompe esto aunque los extremos sobrevivan."""
        # Arrange / Act
        siguiente = interp_angles([0.42, 0.42, 0.42])

        # Assert
        assert siguiente == pytest.approx((0.42, 0.42, 0.42, 0.42))

    def test_una_lista_vacia_explota(self) -> None:
        """No existe "el nivel 0 óptimo": interpolar desde nada devolvería un
        calendario de ceros con cara de warm start."""
        with pytest.raises(ValueError, match="vac"):
            interp_angles([])
