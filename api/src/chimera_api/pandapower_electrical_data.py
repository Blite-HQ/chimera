"""Conversor pandapower network -> InstanceElectricalData (Fase 1, D-2026-07-24).

Extrae buses/slack/branches/loads de una red pandapower ya construida (p.ej.
`pandapower.networks.case6ww()`) al shape que consume `ExecutionVerifier`
(mismo shape que `_SINTETICA_4BUS`, a mano, en instance_verifiers.py).
Reusable: ieee9/ieee14 necesitan el mismo conversor mas adelante -- no se
hardcodea solo para ieee6.

"slack" aqui no es "el slack tecnico" en sentido estricto de pandapower --
es cualquier fuente de voltaje real (ext_grid + gen), porque ExecutionVerifier
crea un pp.create_ext_grid por cada entrada de "slack" que caiga dentro de la
isla (ver engine/src/blite/verification/execution.py::_run_island_powerflow).
"""

from __future__ import annotations

import hashlib
from typing import Any

from blite.verification.execution import ExecutionLimits
from chimera_api.instance_verifiers import InstanceElectricalData


def from_pandapower_network(net: Any, *, provenance: str) -> InstanceElectricalData:
    """Construye un InstanceElectricalData desde una red pandapower ya armada.

    No corre runpp ni valida factibilidad -- eso es responsabilidad de
    ExecutionVerifier en verify(). Esta funcion solo traduce el dato.
    """
    buses = [
        {"id": int(idx), "vn_kv": float(row["vn_kv"])}
        for idx, row in net.bus.iterrows()
    ]

    slack: list[dict[str, Any]] = [
        {"bus": int(row["bus"]), "vm_pu": float(row["vm_pu"])}
        for _, row in net.ext_grid.iterrows()
    ]
    slack += [
        {"bus": int(row["bus"]), "vm_pu": float(row["vm_pu"])}
        for _, row in net.gen.iterrows()
    ]

    branches = [
        {
            "from": int(row["from_bus"]),
            "to": int(row["to_bus"]),
            "r_ohm_per_km": float(row["r_ohm_per_km"]),
            "x_ohm_per_km": float(row["x_ohm_per_km"]),
        }
        for _, row in net.line.iterrows()
        if bool(row["in_service"])
    ]

    loads = [
        {"bus": int(row["bus"]), "p_mw": float(row["p_mw"])}
        for _, row in net.load.iterrows()
    ]

    anchor_digest = hashlib.sha256(f"anchor:{provenance}".encode()).hexdigest()

    return InstanceElectricalData(
        topology={
            "buses": buses,
            "slack": slack,
            "branches": branches,
            "loads": loads,
        },
        limits=ExecutionLimits(),
        anchor_digest=anchor_digest,
        provenance=provenance,
    )
