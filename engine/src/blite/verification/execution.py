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

POWERFLOW_CONVERGED_CHECK = "powerflow_converged"

ABSTENTION_CHECKS = frozenset({POWERFLOW_CONVERGED_CHECK})
"""Checks cuyo fallo es ABSTENCIÓN, no veredicto en contra (spec §1.3): la
no-convergencia es cota del método. Declarado como DATO y no enterrado en el
flujo de `verify()` porque quien LEE la attestation después — el productor de
`partition` (C-8: verdict por isla desde los checks `island-{k}:*`) — necesita
la misma regla para no leer una abstención como un fail."""


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


@dataclass(frozen=True)
class _IslandOutcome:
    """Los checks de una isla + lo que su verdict necesita. Fuente ÚNICA de
    las dos rutas de constancia (global y por isla, C4/M4): si cada una
    corriera su propia evaluación, un cambio en una podría no llegar a la
    otra y el bundle mostraría dos verdades sobre el mismo run."""

    island_id: str
    checks: tuple[ExecutionCheck, ...]
    hard_fail: bool
    inconclusive: bool
    runtime_ms: float


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
        """La constancia GLOBAL — forma intacta (compat: los llamadores y los
        bundles ya emitidos ven exactamente lo mismo que antes de C4/M4)."""
        outcomes, runtime_ms = self._evaluate(claim)
        return self._attestation(
            claim,
            ctx,
            step_id=None,
            checks=tuple(check for outcome in outcomes for check in outcome.checks),
            verdict=derive_execution_verdict(
                all_passed=not any(o.hard_fail for o in outcomes),
                any_inconclusive=any(o.inconclusive for o in outcomes),
            ),
            runtime_ms=runtime_ms,
        )

    def verify_all(self, claim: Any, ctx: InvocationContext) -> tuple[Attestation, ...]:
        """Una constancia POR ISLA (C4/M4 · C-6/#106), con la convención de
        S-D (#125, `docs/specs/superficie-visual.md` §8): verdict de la isla
        `k` = `derive_execution_verdict` sobre el subconjunto de checks
        `island-{k}:*` de esa isla, y `step_id = island_id` estable.

        **Todas comparten `independence_group`** — el del verificador. Es LA
        regla de C-6: partir un verdict global en N verdicts por isla no crea
        N patas independientes; sigue siendo un verificador, un ancla, una
        fuente de evidencia. La granularidad fina existe para EXPLICAR dónde
        falló, no para multiplicar el respaldo de una conclusión.

        La constancia GLOBAL va PRIMERO y las de isla después: la granularidad
        es evidencia ADITIVA, no un reemplazo. Un consumidor que pregunta «¿cómo
        le fue al resultado?» —el productor de `partition` de V1/M18 es
        exactamente ese— no debería tener que re-agregar lo que el verificador
        ya sabe. Todas comparten claim, ancla y grupo, así que el conteo de
        patas del punto 7 sigue dando UNA.

        Ninguna evidencia se pierde ni se duplica: los checks de las dos
        rutas salen de la MISMA evaluación, particionados por isla."""
        outcomes, runtime_ms = self._evaluate(claim)
        global_ = self._attestation(
            claim,
            ctx,
            step_id=None,
            checks=tuple(check for outcome in outcomes for check in outcome.checks),
            verdict=derive_execution_verdict(
                all_passed=not any(o.hard_fail for o in outcomes),
                any_inconclusive=any(o.inconclusive for o in outcomes),
            ),
            runtime_ms=runtime_ms,
        )
        return (
            global_,
            *(
                self._attestation(
                    claim,
                    ctx,
                    step_id=outcome.island_id,
                    checks=outcome.checks,
                    verdict=derive_execution_verdict(
                        all_passed=not outcome.hard_fail,
                        any_inconclusive=outcome.inconclusive,
                    ),
                    runtime_ms=outcome.runtime_ms,
                )
                for outcome in outcomes
            ),
        )

    def _evaluate(self, claim: Any) -> tuple[tuple[_IslandOutcome, ...], float]:
        """Corre los checks UNA vez y los devuelve agrupados por isla — la
        fuente única de las dos rutas (`verify`/`verify_all`)."""
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
        outcomes: list[_IslandOutcome] = []

        islands: dict[int, set[int]] = {}
        for bus, side in zip(bus_ids, claim.assignment, strict=True):
            islands.setdefault(side, set()).add(bus)

        for side in sorted(islands):
            outcomes.append(self._evaluate_island(f"island-{side}", islands[side]))

        return tuple(outcomes), (time.perf_counter() - started) * 1000.0

    def _evaluate_island(self, island_id: str, island: set[int]) -> _IslandOutcome:
        """Los checks de UNA isla, con su verdict propio ya derivable. El
        prefijo `island-{k}:` de cada nombre es la convención de S-D §8 —
        es lo que permite atar cada check a su isla sin adivinar."""
        started = time.perf_counter()
        checks: list[ExecutionCheck] = []
        internal_edges = [
            (int(br["from"]), int(br["to"]))
            for br in self.topology.get("branches", [])
            if int(br["from"]) in island and int(br["to"]) in island
        ]
        connected = _is_connected(island, internal_edges)
        checks.append(
            ExecutionCheck(name=f"{island_id}:island_connectivity", passed=connected)
        )
        sources = {
            int(s["bus"])
            for s in self.topology.get("slack", [])
            if int(s["bus"]) in island
        }
        has_source = bool(sources)
        checks.append(
            ExecutionCheck(name=f"{island_id}:island_has_source", passed=has_source)
        )
        if not (connected and has_source):
            # El flujo de una isla rota no se corre (dependiente).
            return _IslandOutcome(
                island_id=island_id,
                checks=tuple(checks),
                hard_fail=True,
                inconclusive=False,
                runtime_ms=(time.perf_counter() - started) * 1000.0,
            )

        converged, metrics = self._run_island_powerflow(island)
        checks.append(
            ExecutionCheck(
                name=f"{island_id}:{POWERFLOW_CONVERGED_CHECK}", passed=converged
            )
        )
        if not converged:
            # Abstención honesta (spec §1.3): cota del método, no verdict
            return _IslandOutcome(
                island_id=island_id,
                checks=tuple(checks),
                hard_fail=False,
                inconclusive=True,
                runtime_ms=(time.perf_counter() - started) * 1000.0,
            )

        vm = metrics["bus_vm_pu"]
        voltage_ok = all(
            self.limits.vm_pu_min <= v <= self.limits.vm_pu_max for v in vm
        )
        checks.append(
            ExecutionCheck(name=f"{island_id}:voltage_limits", passed=voltage_ok)
        )
        loading_ok = all(
            v <= self.limits.line_loading_max_percent
            for v in metrics["branch_loading_percent"]
        )
        checks.append(
            ExecutionCheck(name=f"{island_id}:line_loading", passed=loading_ok)
        )
        balance_ok = True
        if self.limits.slack_p_max_mw is not None:
            balance_ok = all(
                abs(p) <= self.limits.slack_p_max_mw for p in metrics["slack_p_mw"]
            )
            checks.append(
                ExecutionCheck(name=f"{island_id}:power_balance", passed=balance_ok)
            )
        return _IslandOutcome(
            island_id=island_id,
            checks=tuple(checks),
            hard_fail=not (voltage_ok and loading_ok and balance_ok),
            inconclusive=False,
            runtime_ms=(time.perf_counter() - started) * 1000.0,
        )

    def _attestation(  # noqa: PLR0913 — cada parámetro es un campo distinto de la constancia
        self,
        claim: OptimalityClaim,
        ctx: InvocationContext,
        *,
        step_id: str | None,
        checks: tuple[ExecutionCheck, ...],
        verdict: Verdict,
        runtime_ms: float,
    ) -> Attestation:
        """La constancia — idéntica en las dos rutas salvo `step_id`, los
        checks que ampara y su verdict. El binding (claim/ancla/digests) es
        el MISMO: las islas son vistas del mismo claim, no claims distintos."""
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
            # C-6: TODAS las islas de la corrida comparten el grupo — la
            # granularidad explica, no multiplica patas.
            independence_group=self.independence_group,
            run_id=ctx.run_id,
            step_id=step_id,
            claim_digest=claim_view_digest(claim.canonical_statement, claim.scope),
            verifier_binary_digest=self.verifier_binary_digest,
            verifier_params_digest=self.verifier_params_digest,
            anchor_digest=self.anchor_digest,
            predicate=ExecutionPredicate(
                harness=HARNESS_ID,
                input_digest=hashlib.sha256(canonicalize(input_view)).hexdigest(),
                checks=checks,
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
