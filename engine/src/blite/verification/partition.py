"""
Productor del payload de partición (V1/M18 · C-8/#106,
`docs/specs/superficie-visual.md` §4/§8). [dominio V — visual/ciencia]

El hueco que cierra: el payload de mapa estaba fijado por contrato y la ruta
de lectura lo esperaba (`chimera_api.reads::_project_topology`), pero NADIE lo
emitía — el Studio mostraba honest-empty sobre una superficie que ya tenía
consumidor, esquema y Zod. Este módulo es el emisor que faltaba.

Qué NO hace, y por qué importa: no verifica nada. Traduce una `Attestation`
que YA existe — la que un harness produjo corriendo de verdad — a la forma que
el mapa consume. Si esa attestation no dice nada por isla, este módulo
devuelve `None` y el honest-empty sigue vivo: un badge por isla derivado de un
veredicto global sería exactamente el mock silencioso que la regla 1 del plan
prohíbe.

Las tres reglas del contrato:

- **Verdict por isla** (C-8): el de la isla `k` es `derive_execution_verdict`
  aplicado al SUBCONJUNTO de checks `island-{k}:*` de esa isla. Ningún check
  de otra isla contamina; un check global (sin prefijo) pertenece al
  resultado, no a una isla. La abstención declarada por el harness
  (`ABSTENTION_CHECKS`) se lee como abstención, jamás como fail.
- **Techo de nivel**: una isla nunca reporta MÁS assurance que la attestation
  que la ampara — `level` sale de la attestation, y baja a AL0 cuando la isla
  abstiene (la misma regla que el verificador se aplica a sí mismo).
- **Identidad del corte** (C-8): `cut_branch_ids` cita los ids que la
  instancia trae (`branch_ids`, mitad GIS) o los canónicos derivados de las
  aristas (`blite_capability.branch_ids`) — jamás índices improvisados.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from blite.verification.attestation import Attestation, Verdict
from blite.verification.evidence import ExecutionPredicate, PropertyRulePredicate
from blite.verification.execution import ABSTENTION_CHECKS, derive_execution_verdict
from blite.verification.policy import AssuranceLevel
from blite_capability.branch_ids import canonical_branch_ids

ISLAND_ID_PREFIX = "island-"
"""Prefijo del id de sub-entidad — el mismo que `ExecutionVerifier` estampa en
sus checks y el que C4/M4 usará como `step_id` estable."""

_ISLAND_CHECK_SEPARATOR = ":"

_ABSTAINED_LEVEL: AssuranceLevel = "AL0"


class NamedCheck(Protocol):
    """Lo mínimo que un check aporta acá: su nombre y si pasó. Lo satisfacen
    `ExecutionCheck` y `PropertyCheck` sin que este módulo tenga que elegir
    una clase de verificador — la regla de agregación es la misma."""

    name: str
    passed: bool


def _predicate_checks(attestation: Attestation) -> tuple[NamedCheck, ...]:
    """Los checks nombrados del predicate, o vacío si su clase no los tiene
    (un `formal_exact` no habla de sub-entidades)."""
    predicate = attestation.predicate
    if isinstance(predicate, ExecutionPredicate):
        return predicate.checks
    if isinstance(predicate, PropertyRulePredicate):
        return predicate.properties
    return ()


def split_island_check(name: str) -> tuple[str, str] | None:
    """`"island-0:voltage_limits"` → `("island-0", "voltage_limits")`.

    `None` para un check GLOBAL (sin prefijo de isla): pertenece al resultado,
    no a una isla — C-8 lo dice con todas las letras.
    """
    if not name.startswith(ISLAND_ID_PREFIX):
        return None
    island_id, separator, check_name = name.partition(_ISLAND_CHECK_SEPARATOR)
    if not separator or not check_name:
        return None
    return island_id, check_name


def island_checks_by_island(
    attestation: Attestation,
) -> dict[str, tuple[NamedCheck, ...]]:
    """Checks agrupados por isla, preservando el orden de emisión dentro de
    cada grupo. Un predicate sin checks por isla devuelve `{}` — la señal de
    que esta attestation no ampara ninguna sub-entidad."""
    grouped: dict[str, list[NamedCheck]] = {}
    for check in _predicate_checks(attestation):
        split = split_island_check(check.name)
        if split is None:
            continue
        island_id, _ = split
        grouped.setdefault(island_id, []).append(check)
    return {island: tuple(checks) for island, checks in grouped.items()}


def derive_island_verdict(
    checks: Sequence[NamedCheck], *, abstention_checks: frozenset[str]
) -> Verdict:
    """C-8: `derive_execution_verdict` sobre los checks de UNA isla.

    Un check de abstención que falla NO es un hard-fail (es cota del método);
    cualquier otro que falle sí lo es, y el hard-fail gana sobre la
    abstención (regla de la spec §1.3, reusada tal cual).
    """
    hard_fail = False
    any_inconclusive = False
    for check in checks:
        if check.passed:
            continue
        if _bare_name(check) in abstention_checks:
            any_inconclusive = True
        else:
            hard_fail = True
    return derive_execution_verdict(
        all_passed=not hard_fail, any_inconclusive=any_inconclusive
    )


def _bare_name(check: NamedCheck) -> str:
    """El nombre del check sin su prefijo de isla — para leerlo contra el
    catálogo del harness (que nombra `powerflow_converged`, no
    `island-0:powerflow_converged`)."""
    split = split_island_check(check.name)
    return split[1] if split is not None else check.name


def _summary(island_id: str, checks: Sequence[NamedCheck], verdict: Verdict) -> str:
    """Resumen determinista (el contrato lo exige no vacío) — cita los checks
    que fallaron por nombre, o cuántos pasaron. Sin adjetivos."""
    failed = sorted(_bare_name(check) for check in checks if not check.passed)
    if not failed:
        return f"{island_id}: {len(checks)}/{len(checks)} checks pasaron"
    return f"{island_id}: {verdict} — falló {', '.join(failed)}"


def _method_of(attestation: Attestation) -> str:
    """El método que produjo la constancia: el harness cuando la clase lo
    nombra, si no la clase del predicate."""
    predicate = attestation.predicate
    if isinstance(predicate, ExecutionPredicate):
        return predicate.harness
    return predicate.method


def island_verification(
    island_id: str,
    checks: Sequence[NamedCheck],
    attestation: Attestation,
    *,
    abstention_checks: frozenset[str],
) -> dict[str, Any]:
    """El bloque `verification` de UNA isla (freeze §9, sin excepción)."""
    verdict = derive_island_verdict(checks, abstention_checks=abstention_checks)
    level = _ABSTAINED_LEVEL if verdict == "inconclusive" else attestation.level
    return {
        "verdict": verdict,
        "verifier_class": attestation.verifier_class,
        "level": level,
        "anchor_kind": attestation.anchor_kind,
        "method": _method_of(attestation),
        "summary": _summary(island_id, checks, verdict),
    }


def _buses_by_island(assignment: Sequence[int]) -> dict[str, list[str]]:
    """Bus → isla desde la asignación; los ids viajan como strings del wire y
    en orden ascendente de bus."""
    buses: dict[str, list[str]] = {}
    for bus, side in enumerate(assignment):
        buses.setdefault(f"{ISLAND_ID_PREFIX}{side}", []).append(str(bus))
    return buses


def _resolve_branch_ids(
    edges: Sequence[Sequence[float]], branch_ids: Sequence[str] | None
) -> tuple[str, ...]:
    if branch_ids is None:
        return canonical_branch_ids([[int(e[0]), int(e[1])] for e in edges])
    if len(branch_ids) != len(edges):
        msg = (
            f"branch_ids ({len(branch_ids)}) y aristas ({len(edges)}) deben ir "
            "1:1 — un corte citando ids desalineados nombraría otra rama"
        )
        raise ValueError(msg)
    return tuple(branch_ids)


def _cut(
    assignment: Sequence[int],
    edges: Sequence[Sequence[float]],
    branch_ids: Sequence[str],
) -> tuple[list[str], float]:
    cut_ids: list[str] = []
    cost = 0.0
    for (u, v, *rest), branch_id in zip(edges, branch_ids, strict=True):
        if not (0 <= int(u) < len(assignment) and 0 <= int(v) < len(assignment)):
            msg = f"arista ({u},{v}) fuera de rango para {len(assignment)} buses"
            raise ValueError(msg)
        if assignment[int(u)] == assignment[int(v)]:
            continue
        cut_ids.append(branch_id)
        cost += float(rest[0]) if rest else 1.0
    return cut_ids, cost


def build_partition(
    *,
    attestation: Attestation,
    assignment: Sequence[int],
    edges: Sequence[Sequence[float]],
    topology_ref: str,
    branch_ids: Sequence[str] | None = None,
    island_labels: Mapping[str, str] | None = None,
    abstention_checks: frozenset[str] = ABSTENTION_CHECKS,
) -> dict[str, Any] | None:
    """El payload §4 listo para embeber en `verification.completed`.

    `None` cuando la attestation no ampara ninguna isla — honest-empty, jamás
    un badge por isla prestado del veredicto global.

    Las islas que aparecen son las que el harness VERIFICÓ: una isla de la
    asignación sin checks propios no se lista con un veredicto ajeno.
    """
    grouped = island_checks_by_island(attestation)
    if not grouped:
        return None

    resolved_ids = _resolve_branch_ids(edges, branch_ids)
    cut_ids, cut_cost = _cut(assignment, edges, resolved_ids)
    buses = _buses_by_island(assignment)
    labels = island_labels or {}

    islands = [
        {
            "id": island_id,
            "name": labels.get(island_id, island_id),
            "bus_ids": buses.get(island_id, []),
            "verification": island_verification(
                island_id, checks, attestation, abstention_checks=abstention_checks
            ),
        }
        for island_id, checks in sorted(grouped.items())
    ]
    return {
        "topology_ref": topology_ref,
        "islands": islands,
        "cut_branch_ids": cut_ids,
        "cut_cost": cut_cost,
    }
