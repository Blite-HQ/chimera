"""
Pipeline del gateway — el chokepoint único como mecanismo. [S-G · Steven]

docs/contract-freeze.md §8 [ejecución] (C2, resolución por unión): el orden
es una TUPLA ÚNICA de 8 etapas — `identity → authorization → guardrails →
provenance:pre → mediation → verification → provenance:post → egress`. El
pipeline es explícito e in-process (nota execution/08: jamás middleware —
el orden viviría en el registro de la app, sin handoff tipado ni test de
orden posible), fail-closed en dos sentidos:

- En CONSTRUCCIÓN: una tupla de stages que no calce EXACTAMENTE con
  `STAGE_ORDER` explota al armar el pipeline (misma doctrina que
  `validate_interaction_profile` — fail-closed en deploy, jamás en la
  primera invocación).
- En EJECUCIÓN: un `Rejection` en cualquier etapa corta la cadena — ninguna
  etapa posterior corre. Es la defensa estructural de Inv-E (nota 01 §1.3):
  el egreso jamás se alcanza si `authorization` rechazó, y la etapa de
  egreso ni siquiera SABE leer verdicts de verificación como entrada.

El contrato del `ctx` NO está congelado (nota 01 §10): se usa un mapping
genérico hasta que existan los tipos reales de la capa de confianza
(Identity/AuthzDecision — carril de Dylan). Cada etapa retorna un ctx NUEVO
(inmutabilidad por copia), nunca muta el recibido. INV-4: la etapa que
aplique un override emite su evento ELLA MISMA vía EventStore antes de
aplicarlo (freeze §10) — el Pipeline no decide eso por su cuenta.

Reautorización a mitad de pipeline: NO existe (freeze §8, cerrada) — si el
despacho revela un permiso distinto al evaluado en la etapa 2, es error de
contrato fail-closed; el run falla y se re-invoca completo.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

STAGE_ORDER: tuple[str, ...] = (
    "identity",
    "authorization",
    "guardrails",
    "provenance:pre",
    "mediation",
    "verification",
    "provenance:post",
    "egress",
)

# Forma NO congelada (nota 01 §10/§11): dict genérico hasta que los tipos
# reales de confianza (Identity, AuthzDecision, policy pinneada) existan.
Context = dict[str, Any]


class Rejection(BaseModel):
    """Corte de cadena fail-closed: qué etapa rechazó y por qué."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    stage: str
    reason: str


@runtime_checkable
class Stage(Protocol):
    """Una etapa del chokepoint: lee el ctx, retorna uno nuevo o corta la cadena."""

    @property
    def name(self) -> str:
        """Nombre congelado de la etapa — uno de `STAGE_ORDER`."""
        ...

    def handle(self, ctx: Context) -> Context | Rejection:
        """Retorna un ctx NUEVO (jamás muta el recibido) o un `Rejection`."""
        ...


class PassthroughStage:
    """Etapa no-op (nota 01 §11.2): ocupa su lugar en el orden congelado hasta
    que la implementación real de esa etapa exista — pasa el ctx intacto."""

    def __init__(self, name: str) -> None:
        if name not in STAGE_ORDER:
            msg = f"etapa {name!r} fuera del orden congelado (freeze §8): {STAGE_ORDER}"
            raise ValueError(msg)
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def handle(self, ctx: Context) -> Context | Rejection:
        return ctx


class Pipeline:
    """La tupla fija de etapas del gateway — INV-1 como mecanismo, no aspiración."""

    def __init__(self, stages: tuple[Stage, ...]) -> None:
        names = tuple(stage.name for stage in stages)
        if names != STAGE_ORDER:
            msg = (
                f"las etapas {names!r} no calzan con el orden congelado "
                f"{STAGE_ORDER!r} (freeze §8) — fail-closed en construcción, "
                "jamás en la primera invocación"
            )
            raise ValueError(msg)
        self._stages = stages

    @property
    def stages(self) -> tuple[Stage, ...]:
        return self._stages

    def run(self, ctx: Context) -> Context | Rejection:
        """Ejecuta las 8 etapas en orden; un `Rejection` corta la cadena."""
        current = ctx
        for stage in self._stages:
            result = stage.handle(current)
            if isinstance(result, Rejection):
                return result
            current = result
        return current
