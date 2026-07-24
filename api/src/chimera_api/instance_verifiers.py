"""Registro instancia→verifiers — plan `docs/mvp/01-runtime-api.md` §3.

Módulo PURO (sin FastAPI): resuelve qué adapters del puerto `Verifier`
amparan un claim, dado su `claim_type` y el `instance_id` que lo declara.

Regla fail-closed (decisión #7): CP-SAT (`ExactSolverVerifier`) ampara
SIEMPRE un claim de optimalidad — es el ancla formal, independiente del dato
de la instancia. `ExecutionVerifier` (pandapower) se añade solo cuando la
instancia tiene dato eléctrico registrado (`ELECTRICAL_DATA`); sin él, la
segunda pata simplemente no existe — nunca se inventa. Un `claim_type` fuera
del vocabulario de optimalidad no ampara verificación con nada: resolución
vacía es la señal para que el caller (Task B) devuelva 400 — jamás un run
sin verificación.

Dato semilla `sintetica-4bus` (decisión #8): la misma topología de 4 buses /
dos islas que prueba el golden path real en
`tests/unit/certificate/test_assemble.py::TestDosPatasReales` — coherencia
con el único camino ya probado de punta a punta con anclas reales.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from blite.verification.exact_solver import ExactSolverVerifier
from blite.verification.execution import ExecutionLimits, ExecutionVerifier
from blite.verification.verifier import Verifier

_OPTIMALITY_CLAIM_TYPES = frozenset({"solution"})

_SOLVER_VERIFIER_ID = "verifier:cpsat-differential"
_SOLVER_INDEPENDENCE_GROUP = "leg-formal"
_SOLVER_ANCHOR_PROVENANCE = "cpsat-reference-v1"
_SOLVER_ANCHOR_KIND = "solver"

_EXECUTION_VERIFIER_ID = "verifier:pandapower-islanding"
_EXECUTION_INDEPENDENCE_GROUP = "leg-execution"
_EXECUTION_ANCHOR_KIND = "execution"

SOLVER_ANCHOR_DIGEST = hashlib.sha256(
    f"anchor:{_SOLVER_ANCHOR_PROVENANCE}".encode()
).hexdigest()


@dataclass(frozen=True)
class InstanceElectricalData:
    """Dato eléctrico versionado de una instancia (conocimiento, no código)."""

    topology: dict[str, Any]
    limits: ExecutionLimits
    anchor_digest: str
    provenance: str


@dataclass(frozen=True)
class VerifierResolution:
    """Verifiers que amparan un claim + sus descriptores de ancla, en orden."""

    verifiers: tuple[Verifier, ...]
    anchor_descriptors: tuple[dict[str, Any], ...]


_SINTETICA_4BUS_PROVENANCE = "pandapower-sintetica-v1"

# Topología EXACTA de TestDosPatasReales.TOPOLOGY (4 buses, dos islas
# {0,1}/{2,3}, 3 branches, 2 loads) — el único golden path ya probado con
# CP-SAT y pandapower reales sobre la misma partición.
_SINTETICA_4BUS = InstanceElectricalData(
    topology={
        "buses": [{"id": i, "vn_kv": 20.0} for i in range(4)],
        "slack": [{"bus": 0, "vm_pu": 1.0}, {"bus": 2, "vm_pu": 1.0}],
        "branches": [
            {"from": 0, "to": 1, "r_ohm_per_km": 0.05, "x_ohm_per_km": 0.1},
            {"from": 2, "to": 3, "r_ohm_per_km": 0.05, "x_ohm_per_km": 0.1},
            {"from": 1, "to": 2, "r_ohm_per_km": 0.05, "x_ohm_per_km": 0.1},
        ],
        "loads": [{"bus": 1, "p_mw": 1.0}, {"bus": 3, "p_mw": 1.0}],
    },
    limits=ExecutionLimits(),
    anchor_digest=hashlib.sha256(
        f"anchor:{_SINTETICA_4BUS_PROVENANCE}".encode()
    ).hexdigest(),
    provenance=_SINTETICA_4BUS_PROVENANCE,
)

ELECTRICAL_DATA: dict[str, InstanceElectricalData] = {"sintetica-4bus": _SINTETICA_4BUS}


def _solver_verifier() -> Verifier:
    return ExactSolverVerifier(
        verifier_id=_SOLVER_VERIFIER_ID,
        independence_group=_SOLVER_INDEPENDENCE_GROUP,
        anchor_digest=SOLVER_ANCHOR_DIGEST,
    )


def _solver_descriptor() -> dict[str, Any]:
    return {
        "anchor_digest": SOLVER_ANCHOR_DIGEST,
        "kind": _SOLVER_ANCHOR_KIND,
        "provenance": _SOLVER_ANCHOR_PROVENANCE,
    }


def _execution_verifier(data: InstanceElectricalData) -> Verifier:
    return ExecutionVerifier(
        verifier_id=_EXECUTION_VERIFIER_ID,
        independence_group=_EXECUTION_INDEPENDENCE_GROUP,
        anchor_digest=data.anchor_digest,
        topology=data.topology,
        limits=data.limits,
    )


def _execution_descriptor(data: InstanceElectricalData) -> dict[str, Any]:
    return {
        "anchor_digest": data.anchor_digest,
        "kind": _EXECUTION_ANCHOR_KIND,
        "provenance": data.provenance,
    }


def resolve_verifiers(*, claim_type: str, instance_id: str) -> VerifierResolution:
    """Resuelve los verifiers que amparan `claim_type` sobre `instance_id`.

    Fail-closed: `claim_type` fuera de `_OPTIMALITY_CLAIM_TYPES` devuelve una
    resolución vacía — ninguna instancia rescata un tipo de claim no amparado.
    """
    if claim_type not in _OPTIMALITY_CLAIM_TYPES:
        return VerifierResolution((), ())

    verifiers: list[Verifier] = [_solver_verifier()]
    descriptors: list[dict[str, Any]] = [_solver_descriptor()]

    electrical_data = ELECTRICAL_DATA.get(instance_id)
    if electrical_data is not None:
        verifiers.append(_execution_verifier(electrical_data))
        descriptors.append(_execution_descriptor(electrical_data))

    return VerifierResolution(tuple(verifiers), tuple(descriptors))
