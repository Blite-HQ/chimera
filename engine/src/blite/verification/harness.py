"""
`ExecutionHarness` — el puerto que abre la clase `execution` a dominios que
no son el eléctrico. Ítem C14 (trust/12 §1.4 + trust/04 §1.1).

**El problema que resuelve.** Hoy la clase `execution` tiene UN adapter y ese
adapter es pandapower: «correr de verdad y observar» significa, en el código,
«correr un flujo de potencia». Un dominio que verifica ejecutando otra cosa
—una suite de tests sobre un parche, un simulador de otro campo, un binario
del cliente— no tiene por dónde entrar sin escribir un verificador entero. El
puerto separa las dos mitades: QUÉ significa ejecutar (el harness, específico
del dominio) de QUÉ significa verificar por ejecución (el adapter, genérico).

**Las cuatro fases son el contrato** (trust/12 §1.4): `prepare` deja el
entorno reproducible, `run` ejecuta, `collect` recoge observaciones, y
`dispose` limpia SIEMPRE — incluso si `run` explotó. Un harness que no limpia
convierte la verificación siguiente en una corrida contaminada, y el segundo
resultado ya no significa lo mismo que el primero.

**La guarda PASS_TO_PASS** (el patrón de SWE-bench, trust/12): no basta con
que el test que debía arreglarse pase (`FAIL_TO_PASS`); los que YA pasaban
tienen que seguir pasando. Sin esa mitad, «arreglado» incluye «arreglado
rompiendo otras cosas» — y es exactamente el resultado que un proponente
optimiza si nadie lo mira. Por eso `HarnessOutcome` la exige como conjunto
declarado ANTES de correr, no como una lista que se llena después.

**AX3 (sandboxing exigible) deja de ser aspiracional a nivel de forma:** el
puerto declara `isolation` y el adapter lo estampa en la evidencia, así que
una constancia dice bajo qué aislamiento se produjo. Que un despliegue use
`in_process` es una decisión visible, no un silencio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

Isolation = Literal["in_process", "container", "microvm"]
"""Escalera de aislamiento (trust/12 §1.4 + trust/04 §1.1). `in_process` es
el escalón de hoy y se DECLARA; `microvm` es el ancla general que el mismo
puerto admite sin cambiar de forma."""


@dataclass(frozen=True)
class HarnessSpec:
    """Lo que se va a ejecutar, pinneado. Todo lo que entra al digest de
    parámetros del verificador va aquí: dos corridas con specs distintas no
    son la misma evidencia."""

    harness_id: str
    """`<dominio>-<mecanismo>@<version>` — lo que la constancia cita."""
    isolation: Isolation
    inputs_digest: str
    """Digest del material de entrada (parche, caso, dataset) — el ancla."""
    pass_to_pass: frozenset[str] = frozenset()
    """Los checks que YA pasaban y DEBEN seguir pasando. Declarados ANTES de
    correr: una lista que se llena después no es una guarda, es un reporte."""
    fail_to_pass: frozenset[str] = frozenset()
    """Los que el candidato dice arreglar."""
    params: dict[str, Any] = field(default_factory=dict[str, Any])


@dataclass(frozen=True)
class HarnessOutcome:
    """Lo que el harness OBSERVÓ — datos, jamás un veredicto. Quién juzga es
    el adapter del `Verifier` (freeze §4: la clase y el AL son de la
    constancia, no del ejecutor)."""

    passed: frozenset[str]
    failed: frozenset[str]
    runtime_ms: float
    timed_out: bool = False
    detail: dict[str, Any] = field(default_factory=dict[str, Any])


@runtime_checkable
class ExecutionHarness(Protocol):
    """Las cuatro fases. `dispose` corre SIEMPRE (ver `run_harness`)."""

    @property
    def isolation(self) -> Isolation: ...

    def prepare(self, spec: HarnessSpec) -> None:
        """Deja el entorno listo y REPRODUCIBLE para esta spec."""
        ...

    def run(self, spec: HarnessSpec) -> HarnessOutcome:
        """Ejecuta y observa. Un fallo del PROCESO levanta — jamás se
        disfraza de «todo falló» (misma regla que el resto del plano: error
        ≠ verdict)."""
        ...

    def collect(self, spec: HarnessSpec, outcome: HarnessOutcome) -> HarnessOutcome:
        """Enriquece lo observado con lo que solo el harness sabe (logs,
        artefactos). Separado de `run` para que recoger evidencia no pueda
        cambiar lo ejecutado."""
        ...

    def dispose(self, spec: HarnessSpec) -> None:
        """Limpia. Un harness que no limpia contamina la corrida siguiente y
        el segundo resultado deja de significar lo mismo que el primero."""
        ...


class HarnessProcessError(RuntimeError):
    """Falla del PROCESO de ejecución (el harness no pudo correr), no del
    candidato. Nunca produce constancia — misma distinción dura del freeze §4
    entre `error` y `verdict: fail`."""


def run_harness(harness: ExecutionHarness, spec: HarnessSpec) -> HarnessOutcome:
    """Las cuatro fases en orden, con `dispose` garantizado.

    Es una función y no un método del puerto a propósito: la garantía de
    limpieza no puede depender de que cada implementador se acuerde de
    envolver su propio `run` en un `try/finally`."""
    harness.prepare(spec)
    try:
        outcome = harness.run(spec)
        return harness.collect(spec, outcome)
    finally:
        harness.dispose(spec)


def pass_to_pass_holds(spec: HarnessSpec, outcome: HarnessOutcome) -> tuple[str, ...]:
    """Los checks de la guarda que NO se sostuvieron — vacío = la guarda pasa.

    Un check declarado en `pass_to_pass` que no aparece en `passed` cuenta
    como roto AUNQUE tampoco esté en `failed`: desaparecer de la corrida es
    la forma más limpia de «arreglar» un test incómodo."""
    return tuple(sorted(spec.pass_to_pass - outcome.passed))


__all__ = [
    "ExecutionHarness",
    "HarnessOutcome",
    "HarnessProcessError",
    "HarnessSpec",
    "Isolation",
    "pass_to_pass_holds",
    "run_harness",
]
