"""
Registry de capabilities — descubrimiento tolerante a fallos. [S-G · Steven]

knowledge/execution/04 (cerrada S-E 2026-07-18): opción B adoptada tal cual —
excepción capturada POR entry point individual (jamás un try/except global:
si uno falla, los demás siguen cargando; caso real pyscf/VQE en Windows).
Eventos: `registry.loaded {capability_ids[], failed[]}` /
`registry.capability_load_failed {entry_point, error_kind}` con
`actor_id: service:runtime` en el stream `system:registry` (freeze §2 [S-F·N2]).

Versión duplicada de un id: pin por `DistributionManifest` (via
`version_pins` — el Pydantic completo del manifest es carril de Dylan),
default DETERMINISTA (menor versión en orden lexicográfico), jamás `latest`.
Un pin insatisfacible es fail-closed: el id queda fuera y se registra
`PinnedVersionNotFound` — nunca se elige otra versión en silencio.

ADR-008: este módulo es el ÚNICO puente del engine hacia capabilities, vía
entry points (`importlib.metadata`), nunca imports estáticos de `blite_cap_*`.
El registry es lectura + despacho puro: no decide authz ni verificación
(INV-1 — el chokepoint es el gateway, no el registry).
"""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any, Protocol, runtime_checkable

from blite.events.store import EventStore
from blite_capability.capability import Capability
from blite_capability.manifest import CapabilityManifest
from blite_capability.registry import discover_capabilities

ENTRY_POINT_GROUP = "blite.capabilities"

REGISTRY_LOADED = "registry.loaded"
REGISTRY_CAPABILITY_LOAD_FAILED = "registry.capability_load_failed"

_SYSTEM_REGISTRY_STREAM = "system:registry"
_RUNTIME_ACTOR = "service:runtime"
_SYSTEM_DOMAIN = "system"


@runtime_checkable
class EntryPointLike(Protocol):
    """Lo mínimo que el loader necesita de un entry point (inyectable en tests
    — nota 04 §9; `importlib.metadata.EntryPoint` lo satisface estructuralmente)."""

    @property
    def name(self) -> str:
        """El id de la capability (nombre del entry point)."""
        ...

    def load(self) -> Any:
        """Importa y retorna la clase registrada — la etapa que puede explotar."""
        ...


@runtime_checkable
class Registry(Protocol):
    """Contrato mínimo del registry (nota 04 §1.3): lectura + despacho puro."""

    def list(self) -> tuple[CapabilityManifest, ...]:
        """Manifests de las capabilities que SÍ cargaron, orden determinista por id."""
        ...

    def get(self, capability_id: str) -> Capability:
        """La capability por id; desconocida ⇒ KeyError explícito."""
        ...


class EntryPointRegistry:
    """Registry concreto de Fase 1 — singleton en memoria, construido al arrancar
    (nota 04 §10: sin hot-reload; todas las capabilities viven en el mismo venv)."""

    def __init__(self, capabilities: dict[str, Capability]) -> None:
        self._capabilities = dict(capabilities)

    def list(self) -> tuple[CapabilityManifest, ...]:
        return tuple(
            self._capabilities[cap_id].manifest
            for cap_id in sorted(self._capabilities)
        )

    def get(self, capability_id: str) -> Capability:
        try:
            return self._capabilities[capability_id]
        except KeyError:
            msg = (
                f"capability {capability_id!r} no está en el registry — "
                "o no se instaló, o falló al cargar (ver eventos "
                f"{REGISTRY_CAPABILITY_LOAD_FAILED!r} en {_SYSTEM_REGISTRY_STREAM!r})"
            )
            raise KeyError(msg) from None


def _append_load_failed(store: EventStore, *, entry_point: str, error_kind: str) -> None:
    store.append(
        stream_id=_SYSTEM_REGISTRY_STREAM,
        type=REGISTRY_CAPABILITY_LOAD_FAILED,
        actor_id=_RUNTIME_ACTOR,
        domain_id=_SYSTEM_DOMAIN,
        payload={"entry_point": entry_point, "error_kind": error_kind},
    )


def _select_version(
    candidates: list[Capability], pin: str | None
) -> Capability | None:
    """Resolución de versión duplicada (nota 04 §6, cierre S-E): con pin, SOLO
    la versión pinneada (insatisfacible ⇒ None, fail-closed); sin pin, default
    determinista — la MENOR versión en orden lexicográfico, jamás `latest`."""
    if pin is not None:
        for candidate in candidates:
            if candidate.manifest.version == pin:
                return candidate
        return None
    return min(candidates, key=lambda c: c.manifest.version)


def load_registry(
    store: EventStore,
    *,
    entry_points_source: tuple[EntryPointLike, ...] | None = None,
    version_pins: dict[str, str] | None = None,
) -> EntryPointRegistry:
    """Construye el registry con descubrimiento tolerante a fallos (opción B).

    `entry_points_source` permite inyectar dobles en tests; en producción se
    enumeran los entry points instalados del grupo `blite.capabilities`.
    `version_pins` viene del `DistributionManifest` (carril de Dylan) cuando
    exista — `{capability_id: version}`.
    """
    if entry_points_source is None:
        entry_points_source = tuple(entry_points(group=ENTRY_POINT_GROUP))
    pins = version_pins or {}

    candidates: dict[str, list[Capability]] = {}
    failed: list[str] = []
    for ep in entry_points_source:
        # Captura POR entry point (nunca global): un ImportError de una
        # dependencia opcional no puede tumbar el arranque (nota 04 §1.5).
        try:
            capability_cls = ep.load()
            capability = capability_cls()
            if not isinstance(capability, Capability):
                msg = f"entry point {ep.name!r} no implementa el puerto Capability"
                raise TypeError(msg)
        except Exception as exc:  # noqa: BLE001 — frontera de plugin, fail-soft por diseño
            failed.append(ep.name)
            _append_load_failed(
                store, entry_point=ep.name, error_kind=type(exc).__name__
            )
            continue
        candidates.setdefault(ep.name, []).append(capability)

    selected: dict[str, Capability] = {}
    for cap_id in sorted(candidates):
        chosen = _select_version(candidates[cap_id], pins.get(cap_id))
        if chosen is None:
            failed.append(cap_id)
            _append_load_failed(
                store, entry_point=cap_id, error_kind="PinnedVersionNotFound"
            )
            continue
        selected[cap_id] = chosen

    store.append(
        stream_id=_SYSTEM_REGISTRY_STREAM,
        type=REGISTRY_LOADED,
        actor_id=_RUNTIME_ACTOR,
        domain_id=_SYSTEM_DOMAIN,
        payload={
            "capability_ids": sorted(selected),
            "failed": sorted(failed),
        },
    )
    return EntryPointRegistry(selected)


def load_capabilities() -> dict[str, Capability]:
    """Shim de Fase 1 (descubrimiento estricto vía SDK, sin eventos) — lo usan
    los smoke tests; el camino real del runtime es `load_registry`.

    Capabilities are discovered via Python entry points
    (group="blite.capabilities") — never via direct imports (ADR-008).
    """
    return discover_capabilities()
