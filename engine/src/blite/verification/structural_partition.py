"""
StructuralPartitionVerifier — la pata por sub-entidad que sí existe cuando no
hay ancla de ejecución (V1/M18). [dominio V — visual/ciencia]

El hueco que cierra: `ExecutionVerifier` (AL3, anclado en un simulador de
dominio) es el único
productor de checks `island-{k}:*`, y exige dato eléctrico registrado
(impedancias, cargas, slack). Una instancia derivada de un portal GIS —la red
real que el mapa pinta— trae geometría y nombres, no impedancias. Sin este
verificador, esas instancias no tienen NINGUNA constancia por isla y el mapa
se queda honest-empty para siempre.

La salida honesta no es inventar dato eléctrico: es verificar lo que el grafo
SÍ permite verificar y decirlo con el techo que le corresponde. Clase
`property_rule` ⇒ techo **AL2** (freeze §4), ancla `rule`. El badge dirá AL2,
nunca AL3 — una partición estructuralmente sana puede ser inviable
eléctricamente, y la diferencia entre "conexa" y "el flujo converge" es
exactamente lo que el nivel comunica.

Checks:
- `island-{k}:subgraph_connected` — el subgrafo inducido por la isla es
  conexo con SUS aristas internas (una isla partida en dos pedazos no es una
  isla). Una isla de un solo nodo es conexa por definición.
- `island-{k}:non_empty` — la isla tiene al menos un nodo.
- `cut_edges_nonempty` — GLOBAL (sin prefijo: pertenece al resultado, no a
  una isla, C-8): una asignación que deja todo del mismo lado no particionó
  nada, y eso se reporta en vez de pasar como "todas las islas sanas".
"""

from __future__ import annotations

import hashlib
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from blite.certificate.canonical import JSONValue, canonicalize
from blite.verification.anchor import AnchorKind
from blite.verification.attestation import Attestation, VerifierClass
from blite.verification.claim import claim_view_digest
from blite.verification.context import InvocationContext
from blite.verification.evidence import PropertyCheck, PropertyRulePredicate
from blite.verification.exact_solver import OptimalityClaim, VerificationProcessError
from blite.verification.execution import derive_execution_verdict
from blite.verification.partition import ISLAND_ID_PREFIX
from blite.verification.verifier import Determinism

STRUCTURAL_HARNESS_ID = "structural-partition-v1"

_CUT_NONEMPTY_CHECK = "cut_edges_nonempty"


def _islands_of(assignment: tuple[int, ...]) -> dict[int, set[int]]:
    islands: dict[int, set[int]] = {}
    for node, side in enumerate(assignment):
        islands.setdefault(side, set()).add(node)
    return islands


def _is_connected(nodes: set[int], edges: list[tuple[int, int]]) -> bool:
    """BFS sobre las aristas internas — el mismo chequeo de grafo puro que
    `ExecutionVerifier._is_connected`, acá sobre nodos genéricos."""
    if len(nodes) <= 1:
        return True
    adjacency: dict[int, list[int]] = {node: [] for node in nodes}
    for u, v in edges:
        adjacency[u].append(v)
        adjacency[v].append(u)
    start = next(iter(nodes))
    seen = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in adjacency[node]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return seen == nodes


@dataclass(frozen=True)
class StructuralPartitionVerifier:
    """Adapter de la clase `property_rule` (AL2) sobre un `OptimalityClaim`:
    corre los invariantes de grafo de la partición propuesta, por isla."""

    verifier_id: str
    independence_group: str
    anchor_digest: str
    verifier_binary_digest: str = field(
        default_factory=lambda: hashlib.sha256(
            STRUCTURAL_HARNESS_ID.encode()
        ).hexdigest()
    )

    verifier_class: VerifierClass = field(default="property_rule", init=False)
    anchor_kind: AnchorKind = field(default="rule", init=False)
    determinism: Determinism = field(default="deterministic", init=False)

    @property
    def verifier_params_digest(self) -> str:
        params: dict[str, JSONValue] = {
            "harness": STRUCTURAL_HARNESS_ID,
            "checks": ["subgraph_connected", "non_empty", _CUT_NONEMPTY_CHECK],
        }
        return hashlib.sha256(canonicalize(params)).hexdigest()

    def verify(self, claim: Any, ctx: InvocationContext) -> Attestation:
        if not isinstance(claim, OptimalityClaim):
            msg = f"claim {type(claim).__name__} no es un OptimalityClaim"
            raise VerificationProcessError(msg)

        checks = self._run_checks(claim)
        verdict = derive_execution_verdict(
            all_passed=all(check.passed for check in checks), any_inconclusive=False
        )
        return Attestation(
            verifier_id=self.verifier_id,
            verifier_class=self.verifier_class,
            anchor_kind=self.anchor_kind,
            level="AL2",
            verdict=verdict,
            scope=claim.scope,
            independence_group=self.independence_group,
            run_id=ctx.run_id,
            claim_digest=claim_view_digest(claim.canonical_statement, claim.scope),
            verifier_binary_digest=self.verifier_binary_digest,
            verifier_params_digest=self.verifier_params_digest,
            anchor_digest=self.anchor_digest,
            predicate=PropertyRulePredicate(
                properties=tuple(checks),
                backend=STRUCTURAL_HARNESS_ID,
            ),
            issued_at=datetime.now(UTC),
        )

    def _run_checks(self, claim: OptimalityClaim) -> list[PropertyCheck]:
        islands = _islands_of(claim.assignment)
        checks: list[PropertyCheck] = []
        for side in sorted(islands):
            nodes = islands[side]
            prefix = f"{ISLAND_ID_PREFIX}{side}"
            internal = [
                (u, v) for u, v, _w in claim.instance.edges if u in nodes and v in nodes
            ]
            connected = _is_connected(nodes, internal)
            checks.append(
                PropertyCheck(
                    name=f"{prefix}:subgraph_connected",
                    passed=connected,
                    examples_run=len(internal),
                    counterexample=(
                        None
                        if connected
                        else f"{prefix} se parte: {len(nodes)} nodos, "
                        f"{len(internal)} aristas internas no los conectan"
                    ),
                )
            )
            checks.append(
                PropertyCheck(
                    name=f"{prefix}:non_empty",
                    passed=bool(nodes),
                    examples_run=len(nodes),
                    counterexample=None if nodes else f"{prefix} sin nodos",
                )
            )

        cut = [
            (u, v)
            for u, v, _w in claim.instance.edges
            if claim.assignment[u] != claim.assignment[v]
        ]
        checks.append(
            PropertyCheck(
                name=_CUT_NONEMPTY_CHECK,
                passed=bool(cut),
                examples_run=len(claim.instance.edges),
                counterexample=(
                    None
                    if cut
                    else "ninguna arista cruza: la asignación no particionó nada"
                ),
            )
        )
        return checks
