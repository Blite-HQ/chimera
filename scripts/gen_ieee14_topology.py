#!/usr/bin/env python3
"""Genera la topologia electrica congelada de ieee14 (modelo declarado).

Correr desde la raiz del repo:  uv run python scripts/gen_ieee14_topology.py
Salida: knowledge/islanding/ieee14-topology.json

Task 2 (.superpowers/sdd/task2-brief.md): produce un DATO electrico en el
formato generico de `ExecutionVerifier` (buses/slack/branches/loads + limits)
para que el verifier corra flujo-de-potencia POR ISLA real sobre ieee14.

Modelo declarado single-voltage (D3, docs/mvp/decisiones.md): el formato
generico del verifier solo modela LINEAS (sin transformacion de voltaje) ->
no puede representar fielmente el case14 real (14 buses, voltajes MIXTOS
{0.208,12,14,135} kV, 5 trafos). Se declara una red de UNA sola tension
V0_KV, con el MISMO grafo (20 aristas = 15 lineas + 5 trafos aplanados a
ramas equivalentes) y las MISMAS cargas que case14. El `anchor_digest` que
porta la Attestation pinnea este JSON -> la honestidad esta en DECLARAR el
modelo, no en fingir que reproduce el estado electrico multivoltaje nativo.

Fallback de impedancias (D4, honesto — task2-brief SS"Fallback honesto"):
se intento PRIMERO derivar r/x por rama directamente de case14 (lineas:
r_ohm_per_km/x_ohm_per_km nativos de net.line; trafos: vk_percent/
vkr_percent/sn_mva -> z_ohm en la base V0 via Z_base=V0**2/sn_mva). Con esos
valores el flujo de potencia de la red COMPLETA (las 14 buses en una sola
isla) NO converge: `pandapower.diagnostic` marca 13/20 ramas con |r| o |x|
<= 0.001 ohm (las 8 lineas que en case14 corren al 0.208kV de las lv-side
de los trafos colapsan a impedancia casi nula al reescalar sobre V0=110kV,
dejando la matriz de admitancias mal condicionada para Newton-Raphson).
Se aplican en su lugar impedancias UNIFORMES razonables (orden de magnitud
de una linea de planeamiento a 110kV) a las 20 ramas, calibradas para
converger en banda [0.95,1.05] con holgura amplia (loading maximo medido
<25% del limite declarado) — el GRAFO y las CARGAS siguen siendo de
case14; solo la impedancia por rama es un dato uniforme declarado, no
case14-derivado. Limitacion documentada aqui y en `provenance`.

Slack por isla (convencion, brief SS5): TODOS los buses-fuente de case14
(ext_grid + gen) llevan slack con vm_pu=1.0 -> el ExecutionVerifier promueve
a ext_grid los que caen dentro de cada isla propuesta, asi toda isla que
contenga un bus-fuente tiene fuente propia.
"""

from __future__ import annotations

# pandapower no publica stubs — mismo criterio que engine/capabilities.
# pyright: reportMissingTypeStubs=false
import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pandapower.networks as pn

V0_KV = 110.0
R_OHM_PER_KM_UNIFORME = 0.5
X_OHM_PER_KM_UNIFORME = 1.5
MAX_I_KA = 2.0
VM_PU_MIN = 0.95
VM_PU_MAX = 1.05
LINE_LOADING_MAX_PERCENT = 100.0
SLACK_P_MAX_MW = 400.0  # > carga total case14 (~259 MW) con holgura (brief SS6)
RUTA_SALIDA = Path.cwd() / "knowledge" / "islanding" / "ieee14-topology.json"

PROVENANCE = (
    "modelo declarado single-voltage derivado de pandapower.networks.case14(): "
    "grafo=corpus ieee14 (knowledge/islanding/corpus/ieee14-flujo.json, 20 "
    "aristas, buses 0..13 — el indice de bus de case14 ya es 0..13 ascendente, "
    "el relabel es identidad); cargas=net.load de case14 (p_mw,q_mvar) por "
    f"bus; V0 uniforme {V0_KV} kV en TODOS los buses. NO es el estado "
    "electrico multi-voltaje nativo de case14 (case14 real mezcla "
    "{0.208,12,14,135} kV + 5 transformadores; el formato generico del "
    "verifier solo modela lineas, sin transformacion de voltaje). "
    "Impedancias de rama: se intento PRIMERO derivar r/x por rama desde "
    "case14 (lineas: r_ohm_per_km/x_ohm_per_km nativos; trafos: "
    "vk_percent/vkr_percent/sn_mva -> z_ohm en base V0) y el flujo de la red "
    "COMPLETA no convergio (pandapower.diagnostic: 13/20 ramas con |r| o "
    "|x| <= 0.001 ohm, matriz mal condicionada). Se aplican en su lugar "
    f"impedancias UNIFORMES declaradas ({R_OHM_PER_KM_UNIFORME} + "
    f"j{X_OHM_PER_KM_UNIFORME} ohm, length_km=1.0, max_i_ka={MAX_I_KA}) a "
    "las 20 ramas — orden de magnitud de una linea de planeamiento a "
    "110kV, calibradas para converger en banda con holgura amplia. El "
    "GRAFO (20 aristas) y las CARGAS SI son de case14; la impedancia por "
    "rama es dato uniforme declarado, no case14-derivado. Slack: TODOS los "
    "buses-fuente de case14 (ext_grid+gen) con vm_pu=1.0 — convencion "
    "slack-por-isla, el verifier promueve a ext_grid el/los que caen "
    "dentro de cada isla propuesta. Limitacion honesta documentada "
    "(D3/D4, docs/mvp/decisiones.md; task2-brief.md SS'Fallback honesto')."
)


def _relabel_map(net: Any) -> dict[int, int]:
    buses = sorted(int(b) for b in net.bus.index)
    return {b: k for k, b in enumerate(buses)}


def _fuentes(net: Any, relabel: dict[int, int]) -> list[int]:
    """Buses-fuente de case14 = ext_grid + gen, relabeleados y ordenados."""
    crudos = {int(b) for b in net.ext_grid["bus"]} | {int(b) for b in net.gen["bus"]}
    return sorted(relabel[b] for b in crudos)


def _branches(net: Any, relabel: dict[int, int]) -> list[dict[str, float | int]]:
    pares: list[tuple[int, int]] = []
    for _, fila in net.line[net.line.in_service].iterrows():
        pares.append((relabel[int(fila.from_bus)], relabel[int(fila.to_bus)]))
    for _, fila in net.trafo[net.trafo.in_service].iterrows():
        pares.append((relabel[int(fila.hv_bus)], relabel[int(fila.lv_bus)]))
    pares = [tuple(sorted(p)) for p in pares]
    if len(pares) != len(set(pares)):
        # case14 hoy no tiene ramas paralelas entre el mismo par de buses;
        # si algun dia las tuviera, esta receta necesitaria combinarlas
        # (suma de admitancias) como hace el corpus con los pesos — fail
        # loud en vez de escribir un dato silenciosamente incompleto.
        msg = "ramas paralelas detectadas — la receta no las combina (ver docstring)"
        raise AssertionError(msg)
    return [
        {
            "from": i,
            "to": j,
            "length_km": 1.0,
            "r_ohm_per_km": R_OHM_PER_KM_UNIFORME,
            "x_ohm_per_km": X_OHM_PER_KM_UNIFORME,
            "c_nf_per_km": 0.0,
            "max_i_ka": MAX_I_KA,
        }
        for i, j in sorted(pares)
    ]


def _loads(net: Any, relabel: dict[int, int]) -> list[dict[str, float | int]]:
    return [
        {
            "bus": relabel[int(fila.bus)],
            "p_mw": float(fila.p_mw),
            "q_mvar": float(fila.q_mvar),
        }
        for _, fila in net.load.iterrows()
    ]


def con_digest(envelope: dict[str, Any]) -> dict[str, Any]:
    """digest = SHA-256 del JSON canonico (misma convencion del corpus:
    claves ordenadas, sin espacios, ensure_ascii) SIN el campo digest."""
    canonico = json.dumps(
        envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return {
        **envelope,
        "digest": hashlib.sha256(canonico.encode("utf-8")).hexdigest(),
    }


def construir_envelope() -> dict[str, Any]:
    net = cast(Any, pn).case14()
    relabel = _relabel_map(net)
    n = len(relabel)

    fuentes = _fuentes(net, relabel)
    fuentes_esperadas = [0, 1, 2, 5, 7]  # sonda verificada (task2-brief.md)
    if fuentes != fuentes_esperadas:
        msg = f"buses-fuente de case14 cambiaron: {fuentes} != {fuentes_esperadas}"
        raise AssertionError(msg)

    topology = {
        "buses": [{"id": i, "vn_kv": V0_KV} for i in range(n)],
        "slack": [{"bus": b, "vm_pu": 1.0} for b in fuentes],
        "branches": _branches(net, relabel),
        "loads": _loads(net, relabel),
    }
    limits = {
        "vm_pu_min": VM_PU_MIN,
        "vm_pu_max": VM_PU_MAX,
        "line_loading_max_percent": LINE_LOADING_MAX_PERCENT,
        "slack_p_max_mw": SLACK_P_MAX_MW,
    }
    envelope = {
        "instancia": "ieee14",
        "provenance": PROVENANCE,
        "topology": topology,
        "limits": limits,
    }
    return con_digest(envelope)


def main() -> None:
    envelope = construir_envelope()
    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    RUTA_SALIDA.write_text(
        json.dumps(envelope, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    topology = envelope["topology"]
    print(
        f"ieee14-topology: {len(topology['buses'])} buses, "
        f"{len(topology['branches'])} ramas, {len(topology['loads'])} cargas, "
        f"{len(topology['slack'])} fuentes -> {RUTA_SALIDA}"
    )
    print(f"digest: {envelope['digest']}")


if __name__ == "__main__":
    main()
