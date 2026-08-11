"""
La matriz de convergencia — dos pasadas independientes, cuatro cuadrantes.

**Qué problema resuelve.** Cuando dos fuentes independientes revisan lo mismo
(una simulación y un dueño real; dos auditorías; un agente y una persona), la
pregunta que importa no es «¿cuántos hallazgos hubo?» sino **¿coinciden?**. Si
coinciden, la confianza es máxima. Si una vio algo que la otra no, eso es
información sobre la fuente ciega, no solo sobre el defecto.

```
                     │  LA FUENTE A LO CAZÓ   │  LA FUENTE A NO LO CAZÓ
─────────────────────┼────────────────────────┼─────────────────────────
 LA FUENTE B LO CAZÓ │  (A) CONVERGENCIA      │  (B) GANANCIA DE B
─────────────────────┼────────────────────────┼─────────────────────────
 LA FUENTE B NO      │  (C) SILENCIO DE B     │  (D) CONFLICTO
```

**Lo que este módulo NO hace, y es deliberado: clasificar.** Decidir si dos
hallazgos son «el mismo defecto» es leer y juzgar; una herramienta que lo
adivinara produciría una matriz que se ve rigurosa y no lo es. Lo que sí hace
es **impedir que una clasificación no ganada se convierta en veredicto**.

**Por qué esa es la parte que hay que mecanizar.** En la única corrida real de
este protocolo, la pasada de refutación reclasificó **3 ejes que estaban en A**:
dos fallaban el test del paraguas y uno era ósmosis del auditor, no un
avistamiento independiente. Los tres inflaban A, y **A es lo que sostiene el
veredicto**. El sesgo tiene una dirección conocida: quien construye la matriz
quiere que converja. Las reglas de acá son esa dirección, cerrada.

**Fail-closed en el veredicto.** Dos de los cuatro criterios duros —«ninguna
decisión congelada quedó invalidada» y «la sustancia sobrevivió ambas pasadas»—
no se pueden computar desde la matriz: son afirmaciones sobre el mundo. Se
DECLARAN con evidencia, y sin esa declaración no hay veredicto. Un veredicto
que se emite solo es un veredicto que nadie comprobó.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum


class Quadrant(StrEnum):
    CONVERGENCE = "A"
    GAIN = "B"
    SILENCE = "C"
    CONFLICT = "D"


class Severity(StrEnum):
    NONE = ""
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


VARIANTS: dict[Quadrant, frozenset[str]] = {
    # `parcial`: el track B lo cazó más grueso. Solo cuenta como A si pasa el
    # test del paraguas (`umbrella`).
    Quadrant.CONVERGENCE: frozenset({"", "parcial"}),
    Quadrant.GAIN: frozenset({""}),
    # `verificable` contra el repo ⇒ se aplica (la fuente A es el piso).
    # `dueño` ⇒ solo el dueño puede cerrarlo: el silencio no lo ratifica.
    Quadrant.SILENCE: frozenset({"verificable", "dueño"}),
    # `resuelto`: decisión de dueño acatada y supersesión aplicada.
    Quadrant.CONFLICT: frozenset({"", "resuelto"}),
}


class MatrixError(Exception):
    """La matriz no está bien formada. No se degrada a veredicto parcial."""


@dataclass(frozen=True)
class Axis:
    """Un eje de comparación: UN defecto sobre UN artefacto, visto por 0, 1 o 2
    fuentes. La unidad de la matriz no es «un hallazgo» — es el defecto, que
    puede aparecer con nombres distintos en cada track."""

    id: str
    what: str
    artifact: str
    quadrant: Quadrant
    variant: str = ""
    source_a_evidence: str = ""
    """Puntero primario de la fuente A (`archivo:línea`, corrida, commit)."""
    source_b_evidence: str = ""
    """Puntero primario de la fuente B. Vacío = esta fuente no lo levantó."""
    umbrella: bool | None = None
    """Test del paraguas, SOLO para `A-parcial`: ¿un lector del track grueso,
    sin ver el otro, podría reconstruir el fix específico? Si no, es C."""
    severity: Severity = Severity.NONE
    fix_available: bool = False
    disposition: str = ""


@dataclass(frozen=True)
class Attestation:
    """Un criterio que la matriz NO puede computar, declarado con evidencia."""

    holds: bool
    evidence: str


@dataclass(frozen=True)
class Counts:
    total: int
    by_quadrant: dict[str, int]
    asserted_by_b: int
    """A+B+D: los ejes donde la fuente B afirmó ALGO. Es el denominador
    honesto de la tasa de convergencia — medirla sobre el total premiaría a una
    fuente A que dispara mucho y acierta poco."""
    convergence_rate: float
    blind_spots_of_a: int
    silences_of_b: int
    unresolved_conflicts: int
    p0_without_fix: tuple[str, ...]


@dataclass(frozen=True)
class Verdict:
    converge: bool
    counts: Counts
    reasons: tuple[str, ...] = field(default_factory=tuple)
    """Por qué NO converge. Vacío cuando converge — un veredicto negativo sin
    motivo escrito no es accionable."""


def _validar_eje(axis: Axis) -> None:
    if axis.variant not in VARIANTS[axis.quadrant]:
        permitidas = ", ".join(sorted(VARIANTS[axis.quadrant]) or {"—"})
        msg = (
            f"{axis.id}: variante {axis.variant!r} no existe para el cuadrante "
            f"{axis.quadrant.value} (permitidas: {permitidas})"
        )
        raise MatrixError(msg)

    tiene_a = bool(axis.source_a_evidence.strip())
    tiene_b = bool(axis.source_b_evidence.strip())

    if axis.quadrant is Quadrant.CONVERGENCE:
        if not (tiene_a and tiene_b):
            # La mitigación de independencia parcial: cuando el auditor de una
            # fuente conoce la otra, «coincidimos» sin evidencia primaria propia
            # es ósmosis, no convergencia.
            msg = (
                f"{axis.id}: un eje en A exige evidencia primaria de AMBAS "
                "fuentes. Sin ella no se distingue una convergencia real de "
                "que el auditor ya supiera qué buscar"
            )
            raise MatrixError(msg)
        if axis.variant == "parcial" and axis.umbrella is not True:
            msg = (
                f"{axis.id}: A-parcial sin pasar el test del paraguas. Si un "
                "lector del track grueso no puede reconstruir el fix "
                "específico, el eje es C — no una convergencia parcial"
            )
            raise MatrixError(msg)

    if axis.quadrant is Quadrant.GAIN and (tiene_a or not tiene_b):
        msg = (
            f"{axis.id}: B es «solo la fuente B lo levantó» — exige evidencia "
            "de B y ninguna de A"
        )
        raise MatrixError(msg)

    if axis.quadrant is Quadrant.SILENCE and (not tiene_a or tiene_b):
        msg = (
            f"{axis.id}: C es «solo la fuente A lo levantó» — exige evidencia "
            "de A y ninguna de B"
        )
        raise MatrixError(msg)

    if axis.quadrant is Quadrant.CONFLICT and not (tiene_a and tiene_b):
        msg = f"{axis.id}: un conflicto exige las dos versiones que se contradicen"
        raise MatrixError(msg)


def tally(axes: Sequence[Axis]) -> Counts:
    """Cuenta la matriz, validándola primero. Jamás cuenta una matriz inválida."""
    vistos: set[str] = set()
    for axis in axes:
        if axis.id in vistos:
            msg = f"{axis.id}: eje duplicado — cada defecto se cuenta una vez"
            raise MatrixError(msg)
        vistos.add(axis.id)
        _validar_eje(axis)

    by_quadrant = {q.value: 0 for q in Quadrant}
    for axis in axes:
        by_quadrant[axis.quadrant.value] += 1

    asserted_by_b = by_quadrant["A"] + by_quadrant["B"] + by_quadrant["D"]
    return Counts(
        total=len(axes),
        by_quadrant=by_quadrant,
        asserted_by_b=asserted_by_b,
        convergence_rate=(by_quadrant["A"] / asserted_by_b if asserted_by_b else 0.0),
        blind_spots_of_a=by_quadrant["B"],
        silences_of_b=by_quadrant["C"],
        unresolved_conflicts=sum(
            1
            for axis in axes
            if axis.quadrant is Quadrant.CONFLICT and axis.variant != "resuelto"
        ),
        p0_without_fix=tuple(
            axis.id
            for axis in axes
            if axis.severity is Severity.P0 and not axis.fix_available
        ),
    )


def verdict(
    axes: Sequence[Axis],
    *,
    frozen_decisions_intact: Attestation | None = None,
    substance_survived: Attestation | None = None,
) -> Verdict:
    """CONVERGEN o DIVERGEN, contra los cuatro criterios duros.

    Los dos primeros salen de la matriz. Los dos últimos se DECLARAN: no son
    computables desde acá y pedirlos por argumento es lo que impide emitir un
    veredicto sobre algo que nadie miró.
    """
    counts = tally(axes)
    reasons: list[str] = []

    if counts.unresolved_conflicts:
        reasons.append(
            f"{counts.unresolved_conflicts} conflicto(s) sin resolver — un "
            "conflicto de plano lo cierra su dueño, no la matriz"
        )
    if counts.p0_without_fix:
        reasons.append(f"P0 sin fix aplicable: {', '.join(counts.p0_without_fix)}")

    for nombre, attestation in (
        ("ninguna decisión congelada invalidada", frozen_decisions_intact),
        ("la sustancia sobrevivió ambas pasadas", substance_survived),
    ):
        if attestation is None:
            reasons.append(
                f"criterio «{nombre}» sin declarar — no se computa desde la "
                "matriz, y un veredicto que se emite solo no lo comprobó nadie"
            )
        elif not attestation.holds:
            reasons.append(
                f"criterio «{nombre}» NO se sostiene: {attestation.evidence}"
            )
        elif not attestation.evidence.strip():
            reasons.append(
                f"criterio «{nombre}» declarado sin evidencia — una afirmación "
                "sin puntero no es verificable por nadie más"
            )

    return Verdict(converge=not reasons, counts=counts, reasons=tuple(reasons))
