"""
Despacho por `execution_profile` — freeze §1 (letra [S-F]). [S-G Etapa 0]

docs/contract-freeze.md §1: `DispatchStrategy(Protocol).execute(capability,
inputs) -> Result | JobRef`; `Dispatcher.resolve(execution_profile)`; en Fase 1
solo `InProcessStrategy` es real; `remote-job` retorna `JobRef`, jamás `Result`
síncrono; perfil no soportado ⇒ `NotImplementedError` explícito, nunca fallback
silencioso a in-process.

[S-F] Regla de validez `interaction` × `execution_profile`: la matriz completa
se valida AL CARGAR el `DistributionManifest` — fail-closed en deploy, jamás en
la primera invocación. Override a `remote-job` solo si `interaction: job`;
`interaction: stream` ⇒ `NotImplementedError` en Fase 1; par incompatible ⇒
`NotImplementedError` — la misma doctrina anti-fallback del despacho.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

INTERACTIONS = frozenset({"request_response", "job", "stream"})
EXECUTION_PROFILES = frozenset({"in-process", "service", "remote-job"})


class JobRef(BaseModel):
    """Referencia a un job asíncrono — lo ÚNICO que `remote-job` puede retornar."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str


def validate_interaction_profile(interaction: str, execution_profile: str) -> None:
    """La celda (interaction × profile) es válida o EXPLOTA — freeze §1 [S-F].

    Se llama al cargar el `DistributionManifest` (fail-closed en deploy).
    Valores fuera del vocabulario congelado ⇒ ValueError (jamás aceptar y ver).
    """
    if interaction not in INTERACTIONS:
        msg = f"interaction {interaction!r} fuera del vocabulario congelado (freeze §1)"
        raise ValueError(msg)
    if execution_profile not in EXECUTION_PROFILES:
        msg = f"execution_profile {execution_profile!r} fuera del vocabulario congelado (freeze §1)"
        raise ValueError(msg)
    if interaction == "stream":
        msg = "interaction: stream — valor congelado sin semántica de despacho en Fase 1 (freeze §1 [S-F])"
        raise NotImplementedError(msg)
    if execution_profile == "remote-job" and interaction != "job":
        msg = (
            f"override a remote-job solo si interaction: job — a una capability "
            f"{interaction!r} no se le puede prometer JobRef donde su semántica "
            "promete Result (freeze §1 [S-F])"
        )
        raise NotImplementedError(msg)


@runtime_checkable
class DispatchStrategy(Protocol):
    """`execute(capability, inputs) -> Result | JobRef` (freeze §1)."""

    def execute(self, capability: Any, inputs: dict[str, Any]) -> Any:
        """Ejecuta según el perfil; `remote-job` retorna `JobRef`, jamás Result."""
        ...


@runtime_checkable
class Dispatcher(Protocol):
    """Resuelve la estrategia por perfil; no soportado ⇒ `NotImplementedError`."""

    def resolve(self, execution_profile: str) -> DispatchStrategy:
        """Jamás fallback silencioso a in-process (freeze §1)."""
        ...
