"""Registry real — descubrimiento tolerante a fallos (nota execution/04, cerrada S-E).

Contrato: captura de excepción POR entry point individual (opción B §2/§4 —
si uno falla, los demás siguen cargando); eventos `registry.loaded
{capability_ids[], failed[]}` / `registry.capability_load_failed
{entry_point, error_kind}` con `actor_id: service:runtime` en el stream
`system:registry`; versión duplicada de un id → pin por DistributionManifest,
default DETERMINISTA, jamás `latest`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from blite.events import create_event_store
from blite.runtime.registry import Registry, load_registry
from blite_capability.manifest import CapabilityManifest


def _manifest(cap_id: str, version: str = "0.1.0") -> CapabilityManifest:
    return CapabilityManifest(
        id=cap_id,
        description="generic test capability",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        version=version,
    )


def _capability_cls(cap_id: str, version: str = "0.1.0") -> type:
    class _FakeCapability:
        @property
        def manifest(self) -> CapabilityManifest:
            return _manifest(cap_id, version)

        def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
            return dict(inputs)

    return _FakeCapability


class _ExplodingInit:
    """Simula un manifest/constructor roto (etapa 3 de nota 04 §1.4)."""

    def __init__(self) -> None:
        msg = "broken capability constructor"
        raise RuntimeError(msg)


@dataclass(frozen=True)
class _FakeEntryPoint:
    """Doble del EntryPoint de importlib.metadata (nota 04 §9: simular vía mock)."""

    name: str
    capability_cls: type | None = None
    load_error: type[Exception] | None = None

    def load(self) -> Any:
        if self.load_error is not None:
            raise self.load_error("simulated load failure")
        return self.capability_cls


def test_all_healthy_entry_points_load_and_registry_loaded_is_appended() -> None:
    store = create_event_store()
    eps = (
        _FakeEntryPoint("cap.b", _capability_cls("cap.b")),
        _FakeEntryPoint("cap.a", _capability_cls("cap.a")),
    )

    registry = load_registry(store, entry_points_source=eps)

    assert isinstance(registry, Registry)
    assert [m.id for m in registry.list()] == ["cap.a", "cap.b"]
    assert registry.get("cap.a").manifest.id == "cap.a"

    events = store.read_stream("system:registry")
    assert [e.type for e in events] == ["registry.loaded"]
    loaded = events[0]
    assert loaded.actor_id == "service:runtime"
    assert loaded.payload["capability_ids"] == ["cap.a", "cap.b"]
    assert loaded.payload["failed"] == []


def test_one_failing_entry_point_does_not_block_the_rest() -> None:
    store = create_event_store()
    eps = (
        _FakeEntryPoint("cap.broken", load_error=ImportError),
        _FakeEntryPoint("cap.ok", _capability_cls("cap.ok")),
    )

    registry = load_registry(store, entry_points_source=eps)

    assert [m.id for m in registry.list()] == ["cap.ok"]

    events = store.read_stream("system:registry")
    types = [e.type for e in events]
    assert types == ["registry.capability_load_failed", "registry.loaded"]
    failure = events[0]
    assert failure.actor_id == "service:runtime"
    assert failure.payload == {"entry_point": "cap.broken", "error_kind": "ImportError"}
    assert events[1].payload["capability_ids"] == ["cap.ok"]
    assert events[1].payload["failed"] == ["cap.broken"]


def test_constructor_failure_is_captured_per_entry_point_too() -> None:
    store = create_event_store()
    eps = (
        _FakeEntryPoint("cap.explodes", _ExplodingInit),
        _FakeEntryPoint("cap.ok", _capability_cls("cap.ok")),
    )

    registry = load_registry(store, entry_points_source=eps)

    assert [m.id for m in registry.list()] == ["cap.ok"]
    failure = store.read_stream("system:registry")[0]
    assert failure.type == "registry.capability_load_failed"
    assert failure.payload == {"entry_point": "cap.explodes", "error_kind": "RuntimeError"}


def test_duplicate_id_without_pin_resolves_deterministically_never_latest() -> None:
    store = create_event_store()
    eps = (
        _FakeEntryPoint("cap.dup", _capability_cls("cap.dup", version="0.2.0")),
        _FakeEntryPoint("cap.dup", _capability_cls("cap.dup", version="0.1.0")),
    )

    registry = load_registry(store, entry_points_source=eps)

    # Default determinista: la versión MENOR en orden lexicográfico — jamás
    # "la más nueva gana" implícito (nota 04 §6 "versión duplicada", cierre S-E).
    assert registry.get("cap.dup").manifest.version == "0.1.0"


def test_duplicate_id_with_pin_selects_the_pinned_version() -> None:
    store = create_event_store()
    eps = (
        _FakeEntryPoint("cap.dup", _capability_cls("cap.dup", version="0.1.0")),
        _FakeEntryPoint("cap.dup", _capability_cls("cap.dup", version="0.2.0")),
    )

    registry = load_registry(
        store, entry_points_source=eps, version_pins={"cap.dup": "0.2.0"}
    )

    assert registry.get("cap.dup").manifest.version == "0.2.0"


def test_unsatisfiable_pin_fails_closed_instead_of_picking_another_version() -> None:
    store = create_event_store()
    eps = (_FakeEntryPoint("cap.pinned", _capability_cls("cap.pinned", "0.1.0")),)

    registry = load_registry(
        store, entry_points_source=eps, version_pins={"cap.pinned": "9.9.9"}
    )

    assert registry.list() == ()
    events = store.read_stream("system:registry")
    assert [e.type for e in events] == [
        "registry.capability_load_failed",
        "registry.loaded",
    ]
    assert events[0].payload == {
        "entry_point": "cap.pinned",
        "error_kind": "PinnedVersionNotFound",
    }
    assert events[1].payload["failed"] == ["cap.pinned"]


def test_get_unknown_capability_raises_key_error() -> None:
    store = create_event_store()
    registry = load_registry(store, entry_points_source=())

    with pytest.raises(KeyError):
        registry.get("cap.missing")
