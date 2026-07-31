"""
ExecutionVerifier — el adapter de la clase `execution` (AL3, pandapower)
del puerto Verifier. Nota 12 §1.3: "correr de verdad y observar, no
opinar". [S-G · confianza]

La topología eléctrica y los límites son DATOS del ancla (regla "reglas como
datos"): el `anchor_digest` que porta la Attestation debe pinnear el modelo
de red declarado — el verificador es genérico; los datos de cada instancia
(p.ej. ieee14) son conocimiento versionado aparte (dueño: ciencia).

Checks por isla propuesta (prefijo `island-{k}:`):
- `island_connectivity` — subgrafo interno conexo (chequeo de grafo puro).
- `island_has_source`  — la isla contiene al menos una fuente (slack).
- `powerflow_converged` — el flujo converge; NO convergencia ⇒ inconclusive
  (razón `undecidable`), JAMÁS fail (spec §1.3).
- `voltage_limits` / `line_loading` — banda y carga contra los límites-dato.
- `power_balance` — inyección del slack ≤ límite; activo SOLO si el dato
  `slack_p_max_mw` existe (sin dato de dominio no se inventa el umbral).

Verdict derivado (spec §1.3): todos los hard-checks pasan → pass; algún
hard-fail → fail (gana sobre inconclusive); inconclusive sin hard-fail →
inconclusive. Un fallo del PROCESO (pandapower explota, claim ajeno,
asignación que no casa con la red) levanta `VerificationProcessError`.

Fase 1: pandapower corre in-process (librería confiable y determinista); la
forma queda lista para el puerto Sandbox de Fase 2 (nota 12 §1.4).
"""

from __future__ import annotations

# pandapower no publica stubs — mismo criterio que blite_cap_sim: se silencia
# solo ese reporte y la interacción va tras cast(Any, ...) explícitos.
# pyright: reportMissingTypeStubs=false
import hashlib
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import metadata
from typing import Any, cast

from pydantic import BaseModel, ConfigDict

from blite.certificate.canonical import canonicalize
from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, Verdict, VerifierClass
from blite.verification.claim import claim_view_digest
from blite.verification.context import InvocationContext
from blite.verification.evidence import (
    ExecutionCheck,
    ExecutionEnvironment,
    ExecutionPredicate,
)
from blite.verification.exact_solver import (
    OptimalityClaim,
    VerificationProcessError,
)
from blite.verification.verifier import Determinism

HARNESS_ID = "pandapower-islanding-v1"


class ExecutionLimits(BaseModel):
    """Límites eléctricos como DATO (nota 12). Los defaults son la banda
    estándar de planeamiento — la instancia real los trae de knowledge/."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    vm_pu_min: float = 0.95
    vm_pu_max: float = 1.05
    line_loading_max_percent: float = 100.0
    slack_p_max_mw: float | None = None


def derive_execution_verdict(*, all_passed: bool, any_inconclusive: bool) -> Verdict:
    """Regla exacta de la spec §1.3 — el hard-fail gana sobre la abstención."""
    if not all_passed:
        return "fail"
    if any_inconclusive:
        return "inconclusive"
    return "pass"


def _default_binary_digest() -> str:
    version = metadata.version("pandapower")
    return hashlib.sha256(f"pandapower-{version}".encode()).hexdigest()


def _is_connected(buses: set[int], edges: list[tuple[int, int]]) -> bool:
    """BFS sobre las ramas internas de la isla — chequeo de grafo puro."""
    if len(buses) <= 1:
        return True
    adjacency: dict[int, list[int]] = {b: [] for b in buses}
    for u, v in edges:
        adjacency[u].append(v)
        adjacency[v].append(u)
    start = next(iter(buses))
    seen = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in adjacency[node]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return seen == buses


@dataclass(frozen=True)
class ExecutionVerifier:
    """Adapter de la clase `execution` (AL3): corre el flujo POR ISLA
    propuesta y observa."""

    verifier_id: str
    independence_group: str
    anchor_digest: str
    topology: dict[str, Any]
    limits: ExecutionLimits
    verifier_binary_digest: str = field(default_factory=_default_binary_digest)

    verifier_class: VerifierClass = field(default="execution", init=False)
    anchor_kind: AnchorKind = field(default="execution", init=False)
    determinism: Determinism = field(default="deterministic", init=False)

    @property
    def verifier_params_digest(self) -> str:
        params: dict[str, Any] = {
            "harness": HARNESS_ID,
            "limits": self.limits.model_dump(),
        }
        return hashlib.sha256(canonicalize(params)).hexdigest()

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        if not isinstance(claim, OptimalityClaim):
            msg = f"claim {type(claim).__name__} no es un OptimalityClaim"
            raise VerificationProcessError(msg)
        bus_ids = [int(b["id"]) for b in self.topology.get("buses", [])]
        if len(claim.assignment) != len(bus_ids):
            msg = (
                f"asignación de largo {len(claim.assignment)} no casa con la "
                f"topología declarada ({len(bus_ids)} buses) — error de proceso"
            )
            raise VerificationProcessError(msg)

        started = time.perf_counter()
        checks: list[ExecutionCheck] = []
        hard_fail = False
        any_inconclusive = False

        islands: dict[int, set[int]] = {}
        for bus, side in zip(bus_ids, claim.assignment, strict=True):
            islands.setdefault(side, set()).add(bus)

        for side in sorted(islands):
            island = islands[side]
            prefix = f"island-{side}"
            internal_edges = [
                (int(br["from"]), int(br["to"]))
                for br in self.topology.get("branches", [])
                if int(br["from"]) in island and int(br["to"]) in island
            ]
            connected = _is_connected(island, internal_edges)
            checks.append(
                ExecutionCheck(name=f"{prefix}:island_connectivity", passed=connected)
            )
            sources = {
                int(s["bus"])
                for s in self.topology.get("slack", [])
                if int(s["bus"]) in island
            }
            has_source = bool(sources)
            checks.append(
                ExecutionCheck(name=f"{prefix}:island_has_source", passed=has_source)
            )
            if not (connected and has_source):
                hard_fail = True
                continue  # el flujo de una isla rota no se corre (dependiente)

            converged, metrics = self._run_island_powerflow(island)
            checks.append(
                ExecutionCheck(name=f"{prefix}:powerflow_converged", passed=converged)
            )
            if not converged:
                # Abstención honesta (spec §1.3): cota del método, no verdict
                any_inconclusive = True
                continue

            vm = metrics["bus_vm_pu"]
            voltage_ok = all(
                self.limits.vm_pu_min <= v <= self.limits.vm_pu_max for v in vm
            )
            checks.append(
                ExecutionCheck(name=f"{prefix}:voltage_limits", passed=voltage_ok)
            )
            loading_ok = all(
                v <= self.limits.line_loading_max_percent
                for v in metrics["branch_loading_percent"]
            )
            checks.append(
                ExecutionCheck(name=f"{prefix}:line_loading", passed=loading_ok)
            )
            balance_ok = True
            if self.limits.slack_p_max_mw is not None:
                balance_ok = all(
                    abs(p) <= self.limits.slack_p_max_mw for p in metrics["slack_p_mw"]
                )
                checks.append(
                    ExecutionCheck(name=f"{prefix}:power_balance", passed=balance_ok)
                )
            if not (voltage_ok and loading_ok and balance_ok):
                hard_fail = True

        runtime_ms = (time.perf_counter() - started) * 1000.0
        verdict = derive_execution_verdict(
            all_passed=not hard_fail, any_inconclusive=any_inconclusive
        )
        input_view: dict[str, Any] = {
            "topology": self.topology,
            "assignment": list(claim.assignment),
            "limits": self.limits.model_dump(),
        }
        return Attestation(
            verifier_id=self.verifier_id,
            verifier_class=self.verifier_class,
            anchor_kind=self.anchor_kind,
            level="AL3" if verdict != "inconclusive" else "AL0",
            verdict=verdict,
            inconclusive_reason=("undecidable" if verdict == "inconclusive" else None),
            scope=claim.scope,
            independence_group=self.independence_group,
            run_id=ctx.run_id,
            claim_digest=claim_view_digest(claim.canonical_statement, claim.scope),
            verifier_binary_digest=self.verifier_binary_digest,
            verifier_params_digest=self.verifier_params_digest,
            anchor_digest=self.anchor_digest,
            predicate=ExecutionPredicate(
                harness=HARNESS_ID,
                input_digest=hashlib.sha256(canonicalize(input_view)).hexdigest(),
                checks=tuple(checks),
                runtime_ms=runtime_ms,
                environment=ExecutionEnvironment(
                    package="pandapower", version=metadata.version("pandapower")
                ),
            ),
            issued_at=datetime.now(UTC),
        )

    def _run_island_powerflow(
        self, island: set[int]
    ) -> tuple[bool, dict[str, list[float]]]:
        """Construye la sub-red de la isla y corre `pp.runpp`.

        No-convergencia retorna `(False, {})`; cualquier otra explosión de
        pandapower es un error de PROCESO y levanta (fail-loud).
        """
        import pandapower as pp
        from pandapower.powerflow import LoadflowNotConverged

        try:
            net = cast(Any, pp).create_empty_network()
            bus_index: dict[int, int] = {}
            for bus in self.topology.get("buses", []):
                if int(bus["id"]) not in island:
                    continue
                bus_index[int(bus["id"])] = int(
                    cast(Any, pp).create_bus(net, vn_kv=float(bus["vn_kv"]))
                )
            for source in self.topology.get("slack", []):
                if int(source["bus"]) not in island:
                    continue
                cast(Any, pp).create_ext_grid(
                    net,
                    bus=bus_index[int(source["bus"])],
                    vm_pu=float(source.get("vm_pu", 1.0)),
                )
            for branch in self.topology.get("branches", []):
                if not (int(branch["from"]) in island and int(branch["to"]) in island):
                    continue
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
            for load in self.topology.get("loads", []):
                if int(load["bus"]) not in island:
                    continue
                cast(Any, pp).create_load(
                    net,
                    bus=bus_index[int(load["bus"])],
                    p_mw=float(load["p_mw"]),
                    q_mvar=float(load.get("q_mvar", 0.0)),
                )
        except Exception as exc:
            msg = f"construcción de la sub-red de la isla falló: {exc!r}"
            raise VerificationProcessError(msg) from exc

        try:
            cast(Any, pp).runpp(net)
        except LoadflowNotConverged:
            return False, {}
        except Exception as exc:
            msg = f"pandapower explotó fuera de no-convergencia: {exc!r}"
            raise VerificationProcessError(msg) from exc

        res_bus = net.res_bus
        res_line = net.res_line
        res_ext = net.res_ext_grid
        return True, {
            "bus_vm_pu": [float(v) for v in res_bus["vm_pu"]],
            "branch_loading_percent": [float(v) for v in res_line["loading_percent"]],
            "slack_p_mw": [float(v) for v in res_ext["p_mw"]],
        }
