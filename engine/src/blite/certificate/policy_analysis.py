"""
Análisis del SET de políticas — «probar que la regla nueva no es menos
estricta». Ítem C13 (trust/13 §1.1-1.2, forma de Cedar Analysis).

**Qué problema resuelve.** `policy_diff.py` compara TEXTO: dice qué líneas
cambiaron. Eso no responde la única pregunta que importa al cambiar una
política de verificación — *¿algún caso quedó con menos exigencia que
antes?* — porque una política es un conjunto de reglas que interactúan: se
puede aflojar un caso agregando una regla, quitando una restricción de
`match` (¡ampliándola!) o reordenando. Un diff de texto muestra las tres como
«+3 -1».

**La idea que se adopta de Cedar Analysis, sin su motor:** razonar sobre las
PROPIEDADES del set, no sobre las líneas. Acá el dominio es finito y chico
—las combinaciones `(claim_type, side_effects)` que las dos políticas
nombran—, así que la comparación es exhaustiva por enumeración y no hace
falta un SMT: para cada caso se computa la exigencia con el MISMO evaluador
que usa el checklist (`bundle_check.requirement_for`) y se comparan. Usar el
mismo evaluador no es economía: un analizador con su propia noción de
«exigencia» respondería sobre una política que nadie aplica.

**La garantía de claims, aplicada a las políticas.** El resultado es la misma
clase de afirmación que produce el resto del sistema: no «confía en que
revisé el diff», sino «ningún caso del dominio enumerado quedó más laxo, y
estos son los casos».
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from blite.certificate.bundle_check import Exigencia, requirement_for

_LEVEL_ORDER: dict[str, int] = {"AL0": 0, "AL1": 1, "AL2": 2, "AL3": 3, "AL4": 4}

_SIDE_EFFECTS = ("pure", "irreversible-external", None)
"""Los efectos que un claim puede DECLARAR hoy (§6 [stress-final]: derivados
del flag `irreversible` del `●ClaimEmitted`), más el caso sin declarar —
que es un caso real y el más peligroso de olvidar."""


@dataclass(frozen=True)
class Relajacion:
    """Un caso que la política nueva exige MENOS que la vieja."""

    claim_type: str | None
    side_effects: str | None
    antes: Exigencia | None
    despues: Exigencia | None
    motivo: str

    def __str__(self) -> str:  # pragma: no cover — formato de reporte
        caso = f"claim_type={self.claim_type!r}, side_effects={self.side_effects!r}"
        return f"{caso}: {self.motivo}"


def _casos(*rule_sets: list[dict[str, Any]]) -> list[tuple[str | None, str | None]]:
    """El dominio a enumerar: los `claim_type` que CUALQUIERA de las dos
    políticas nombra (más `None`, el claim sin tipo) × los efectos posibles.
    Tomar solo los de la política nueva escondería justo el caso que la vieja
    cubría y la nueva no."""
    claim_types: set[str | None] = {None}
    for rules in rule_sets:
        for rule in rules:
            tipo = rule.get("match", {}).get("claim_type")
            if tipo is not None:
                claim_types.add(str(tipo))
    return [
        (tipo, efecto)
        for tipo in sorted(claim_types, key=str)
        for efecto in _SIDE_EFFECTS
    ]


def _mas_laxa(antes: Exigencia | None, despues: Exigencia | None) -> str | None:
    """Por qué `despues` exige menos que `antes` — `None` si no exige menos.

    Perder la cobertura (había regla y ya no) es la relajación más grande de
    todas: el caso pasa de tener exigencia a no tener ninguna."""
    if antes is None:
        return None
    if despues is None:
        return "la política nueva no cubre este caso (antes sí)"
    razones: list[str] = []
    if _LEVEL_ORDER[despues.min_level] < _LEVEL_ORDER[antes.min_level]:
        razones.append(f"min_level baja de {antes.min_level} a {despues.min_level}")
    if despues.required_legs < antes.required_legs:
        razones.append(
            f"patas exigidas bajan de {antes.required_legs} a {despues.required_legs}"
        )
    perdidas = set(antes.required_anchors) - set(despues.required_anchors)
    if perdidas:
        razones.append(f"deja de exigir anclas {sorted(perdidas)}")
    return "; ".join(razones) or None


def analizar_relajaciones(
    antes_yaml: bytes, despues_yaml: bytes
) -> tuple[Relajacion, ...]:
    """Los casos donde la política NUEVA exige menos que la vieja.

    Tupla vacía = la nueva es al menos tan estricta en todo el dominio
    enumerado. Ese enunciado es exactamente lo que un cambio de política
    debería poder demostrar antes de mergearse."""
    antes: list[dict[str, Any]] = yaml.safe_load(antes_yaml).get("rules", [])
    despues: list[dict[str, Any]] = yaml.safe_load(despues_yaml).get("rules", [])

    hallazgos: list[Relajacion] = []
    for claim_type, side_effects in _casos(antes, despues):
        conclusion = {"claim_digest": "caso", "claim_type": claim_type}
        efectos = {"caso": side_effects} if side_effects is not None else {}
        exigencia_antes = requirement_for(antes, conclusion, efectos)
        exigencia_despues = requirement_for(despues, conclusion, efectos)
        motivo = _mas_laxa(exigencia_antes, exigencia_despues)
        if motivo is not None:
            hallazgos.append(
                Relajacion(
                    claim_type=claim_type,
                    side_effects=side_effects,
                    antes=exigencia_antes,
                    despues=exigencia_despues,
                    motivo=motivo,
                )
            )
    return tuple(hallazgos)


__all__ = ["Relajacion", "analizar_relajaciones"]
