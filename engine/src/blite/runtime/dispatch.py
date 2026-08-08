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

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from blite_capability.capability import Capability

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


class InProcessStrategy:
    """ÚNICA estrategia real de Fase 1 (freeze §1, nota execution/06 §11):
    llamada de función directa en el mismo proceso — sin red, sin serialización.

    Retorna el Result directo de `Capability.invoke()`; un `JobRef` es lo
    ÚNICO que `remote-job` (sin estrategia en Fase 1) podría retornar.
    """

    def execute(self, capability: Capability, inputs: dict[str, Any]) -> dict[str, Any]:
        return capability.invoke(inputs)


class ServiceStrategy:
    """`execution_profile: service` — la capability corre FUERA de este proceso.

    Genérica a propósito: recibe el invocador INYECTADO en vez de importar el
    adapter. `runtime` no hace egreso (eso vive en `blite.protocols`, por encima
    de `authz` — INV-6), igual que no construye el gateway ni el proposer: define
    el seam y la raíz de composición enchufa. Sin esta inyección, agregar un
    transporte metería egreso dentro del loop.

    Devuelve `Result`, no `JobRef`: `service` es síncrono por contrato — quien
    quiera asincronía pide `remote-job`, que tiene su propia celda en la matriz.
    """

    def __init__(
        self, invoker: Callable[[str, dict[str, Any]], dict[str, Any]]
    ) -> None:
        self._invoker = invoker

    def execute(self, capability: Capability, inputs: dict[str, Any]) -> dict[str, Any]:
        return self._invoker(capability.manifest.id, inputs)


class ProfileDispatcher:
    """Tabla de despacho `{execution_profile: DispatchStrategy}` con UNA sola
    entrada real (nota execution/06 §11) — resuelve por VALOR del perfil, nunca
    por identidad de una capability (ADR-029).

    Perfil del contrato sin estrategia ⇒ `NotImplementedError` explícito —
    nunca fallback silencioso a in-process, porque escondería el modo de falla
    central de la nota 06 §6 (tratar `remote-job` como síncrono). Valor fuera
    del vocabulario congelado ⇒ `ValueError` (jamás aceptar y ver).

    `remote-job` gana estrategia SOLO si se inyecta una cola (P11): sin cola
    sigue siendo `NotImplementedError` — un despliegue sin cola no puede
    fingir que corre trabajos largos. `service` gana estrategia SOLO si se
    inyecta un invocador (O5/M13): sin él, una capability de perfil `service`
    NO se ejecuta in-process a escondidas — se saltaría la allowlist, el pin y
    la attestation del despliegue.
    """

    def __init__(
        self,
        remote_job: DispatchStrategy | None = None,
        service: DispatchStrategy | None = None,
    ) -> None:
        self._strategies: dict[str, DispatchStrategy] = {
            "in-process": InProcessStrategy(),
        }
        if remote_job is not None:
            self._strategies["remote-job"] = remote_job
        if service is not None:
            self._strategies["service"] = service

    def resolve(self, execution_profile: str) -> DispatchStrategy:
        if execution_profile not in EXECUTION_PROFILES:
            msg = (
                f"execution_profile {execution_profile!r} fuera del vocabulario "
                "congelado (freeze §1)"
            )
            raise ValueError(msg)
        strategy = self._strategies.get(execution_profile)
        if strategy is None:
            msg = (
                f"execution_profile {execution_profile!r} existe en el contrato "
                "(freeze §1) pero no tiene estrategia real en Fase 1 — jamás "
                "fallback silencioso a in-process (nota execution/06 §11)"
            )
            raise NotImplementedError(msg)
        return strategy
