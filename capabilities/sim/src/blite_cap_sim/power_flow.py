"""Corrida de flujo de potencia con pandapower sobre una topología genérica.

Formato de `topology` (dicts genéricos — ADR-029, el manifest no cambia):

    {
      "buses":    [{"id": int, "vn_kv": float}, ...],
      "slack":    [{"bus": int, "vm_pu": float = 1.0}, ...],
      "branches": [{"from": int, "to": int, "length_km": float = 1.0,
                    "r_ohm_per_km": float, "x_ohm_per_km": float,
                    "c_nf_per_km": float = 0.0, "max_i_ka": float = 1.0}, ...],
      "loads":    [{"bus": int, "p_mw": float, "q_mvar": float = 0.0}, ...],
    }

Salida según el output_schema del manifest: `{"converged": bool, "metrics": {...}}`
— la no-convergencia es resultado, no excepción (el esquema la modela).
"""

from __future__ import annotations

from typing import Any, cast


def _require_section(topology: dict[str, Any], key: str) -> list[dict[str, Any]]:
    section = topology.get(key)
    if not isinstance(section, list) or not section:
        msg = f"PowerFlowSim: topology.{key} (lista no vacía) es requerida"
        raise ValueError(msg)
    return cast("list[dict[str, Any]]", section)


def _build_network(topology: dict[str, Any]) -> Any:
    import pandapower as pp

    buses = _require_section(topology, "buses")
    slack = _require_section(topology, "slack")
    branches = cast("list[dict[str, Any]]", topology.get("branches") or [])
    loads = cast("list[dict[str, Any]]", topology.get("loads") or [])

    net = cast(Any, pp).create_empty_network()
    bus_index: dict[int, int] = {}
    for bus in buses:
        bus_index[int(bus["id"])] = int(
            cast(Any, pp).create_bus(net, vn_kv=float(bus["vn_kv"]))
        )
    for source in slack:
        cast(Any, pp).create_ext_grid(
            net,
            bus=bus_index[int(source["bus"])],
            vm_pu=float(source.get("vm_pu", 1.0)),
        )
    for branch in branches:
        cast(Any, pp).create_line_from_parameters(
            net,
            from_bus=bus_index[int(branch["from"])],
            to_bus=bus_index[int(branch["to"])],
            length_km=float(branch.get("length_km", 1.0)),
            r_ohm_per_km=float(branch["r_ohm_per_km"]),
            x_ohm_per_km=float(branch["x_ohm_per_km"]),
            c_nf_per_km=float(branch.get("c_nf_per_km", 0.0)),
            max_i_ka=float(branch.get("max_i_ka", 1.0)),
        )
    for load in loads:
        cast(Any, pp).create_load(
            net,
            bus=bus_index[int(load["bus"])],
            p_mw=float(load["p_mw"]),
            q_mvar=float(load.get("q_mvar", 0.0)),
        )
    return net


def _metrics_of(net: Any) -> dict[str, Any]:
    res_bus = cast(Any, net).res_bus
    res_line = cast(Any, net).res_line
    return {
        "bus_vm_pu": [float(v) for v in res_bus["vm_pu"]],
        "bus_va_degree": [float(v) for v in res_bus["va_degree"]],
        "branch_p_from_mw": [float(v) for v in res_line["p_from_mw"]],
        "branch_loading_percent": [float(v) for v in res_line["loading_percent"]],
        "total_losses_mw": float(sum(float(v) for v in res_line["pl_mw"])),
    }


def run_power_flow(topology: dict[str, Any]) -> dict[str, Any]:
    """Construye la red, corre `pp.runpp` y devuelve convergencia + métricas."""
    import pandapower as pp
    from pandapower.powerflow import LoadflowNotConverged

    net = _build_network(topology)
    try:
        cast(Any, pp).runpp(net)
    except LoadflowNotConverged:
        return {"converged": False, "metrics": {}}
    return {"converged": True, "metrics": _metrics_of(net)}
