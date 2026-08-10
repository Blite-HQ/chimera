"""Warm start de ángulos QAOA — la heurística INTERP (V5).

El problema que resuelve: arrancar COBYLA en un punto constante (0.1, 0.1, …)
es arbitrario, y su costo crece con p porque el paisaje variacional se vuelve
más rugoso — a p alto el optimizador local se queda en el primer valle que
encuentra y la curva r vs p deja de subir por razones del OPTIMIZADOR, no de
QAOA. Zhou et al. (2020) §IV observan que los calendarios óptimos (β, γ) son
suaves en el índice de capa, y proponen inicializar el nivel p+1 interpolando
linealmente el óptimo del nivel p.

La fórmula, con γ₀ ≡ γ_{p+1} ≡ 0:

    γᵢ^(p+1) = ((i−1)/p)·γ_{i−1}^(p) + ((p−i+1)/p)·γᵢ^(p),   i = 1…p+1

Es aditivo por diseño: `solve_qaoa` sigue arrancando constante salvo que se
le pida otra cosa. Un warm start cambia DÓNDE empieza a buscar el
optimizador, jamás qué se mide después — el ⟨C⟩ reportado se evalúa sobre el
circuito final igual que siempre.
"""

from __future__ import annotations

from collections.abc import Sequence


def interp_angles(level_angles: Sequence[float]) -> tuple[float, ...]:
    """Extiende un calendario de ángulos de p capas a uno de p+1.

    Los coeficientes suman 1 para cada i, así que el resultado es una
    combinación convexa de ángulos vecinos: interpolar nunca inventa un
    ángulo fuera del rango del calendario original.
    """
    p = len(level_angles)
    if p < 1:
        msg = "interp_angles: el calendario de origen no puede estar vacío"
        raise ValueError(msg)

    def angle(i: int) -> float:
        """Ángulo 1-based; 0.0 fuera del calendario (las fronteras γ₀/γ_{p+1}
        de la fórmula, que son las que conservan los extremos)."""
        return float(level_angles[i - 1]) if 1 <= i <= p else 0.0

    return tuple(
        ((i - 1) / p) * angle(i - 1) + ((p - i + 1) / p) * angle(i)
        for i in range(1, p + 2)
    )
