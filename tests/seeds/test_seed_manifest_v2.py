"""Seed del manifest v2 en el SDK (S-E, decisión #127 — freeze §1).

Contrato: docs/specs/manifest-v2-sdk.md. Los 4 campos congelados aterrizan en
`blite_capability.manifest`; sin defaults para el riesgo (#127). El xfail se
retira cuando C1 migre el SDK (y las 13 capabilities, en el mismo checkpoint).

Directiva pyright per-file: los campos objetivo no existen por diseño hasta
Fase 1; la directiva se retira junto con el xfail.
"""

# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# pyright: reportUnknownMemberType=false

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason=(
            "Fase 1 C1: CapabilityManifest sigue en v1 (sin los 4 campos §1) — "
            "docs/specs/manifest-v2-sdk.md (#127)"
        ),
    ),
]

_SCHEMA: dict[str, object] = {"type": "object"}


def test_los_cuatro_campos_con_default_solo_en_profile() -> None:
    """Letra §1: execution_profile default in-process; el resto explícito."""
    from blite_capability.manifest import CapabilityManifest

    manifest = CapabilityManifest(
        id="blite.example.echo",
        description="generic echo",
        input_schema=_SCHEMA,
        output_schema=_SCHEMA,
        side_effects="pure",
        required_permission="capability:invoke",
        interaction="request_response",
    )
    assert manifest.execution_profile == "in-process"
    assert manifest.side_effects == "pure"


def test_side_effects_obligatorio_fail_closed() -> None:
    """#127: defaultear el eje de riesgo miente — construir sin él explota."""
    from blite_capability.manifest import CapabilityManifest

    with pytest.raises(TypeError):
        CapabilityManifest(
            id="blite.example.echo",
            description="generic echo",
            input_schema=_SCHEMA,
            output_schema=_SCHEMA,
        )


def test_literal_invalido_explota_en_post_init() -> None:
    """#127: __post_init__ valida los literals — ValueError al cargar."""
    from blite_capability.manifest import CapabilityManifest

    with pytest.raises(ValueError):
        CapabilityManifest(
            id="blite.example.echo",
            description="generic echo",
            input_schema=_SCHEMA,
            output_schema=_SCHEMA,
            side_effects="mostly-harmless",
            required_permission="capability:invoke",
            interaction="request_response",
        )
